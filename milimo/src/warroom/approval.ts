import { readdirSync, readFileSync, renameSync, unlinkSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';
import { parse as yamlParse } from 'yaml';
import { AuditLogger } from './audit';
import { RateLimiter, Tier, getTierFromString } from './rate-limiter';

export type ApprovalMode = 'AUTO' | 'REVIEW' | 'HOLD' | 'VETO';

export interface PendingMessage {
  message_id: string;
  sender_role: string;
  recipient_role: string;
  message_type: string;
  payload: any;
  squad_id: string;
  timestamp: string;
  needs_approval: boolean;
  file_path: string;
}

export interface EscalationRule {
  trigger: string;
  action: ApprovalMode;
  description: string;
}

export class ApprovalEngine {
  private meshDir: string;
  private warRoomInbox: string;
  private audit: AuditLogger;
  private escalationRules: EscalationRule[] = [];
  private rateLimiter: RateLimiter | null = null;
  private tier: Tier = Tier.FREE;

  constructor(squadId: string, tier: string = 'free') {
    const home = process.env.HOME || process.env.USERPROFILE || homedir() || '/tmp';
    this.meshDir = join(home, '.milimo', 'mesh');
    this.warRoomInbox = join(this.meshDir, 'inbox', 'war_room');
    this.audit = new AuditLogger(squadId);
    this.tier = getTierFromString(tier);

    // Initialize rate limiter
    try {
      this.rateLimiter = new RateLimiter(this.tier, join(home, '.milimo'));
    } catch (e) {
      console.warn('Failed to initialize rate limiter:', e);
    }

    this.loadEscalationRules();
  }

  private loadEscalationRules() {
    try {
      const configPath = join(process.cwd(), 'milimo-blueprint', 'mesh_config.yaml');
      const content = readFileSync(configPath, 'utf8');
      const config = yamlParse(content);
      if (config && config.escalation_rules) {
        this.escalationRules = config.escalation_rules.map((rule: any) => ({
          trigger: rule.trigger,
          action: rule.action.toUpperCase() as ApprovalMode,
          description: rule.description,
        }));
      }
    } catch (e) {
      console.warn('Failed to load escalation rules from mesh_config.yaml. Using defaults.');
      this.escalationRules = [
        { trigger: 'invoice_over_500', action: 'VETO', description: 'Any invoice >$500 requires squad-wide approval' }
      ];
    }
  }

  public getPendingMessages(): PendingMessage[] {
    try {
      const files = readdirSync(this.warRoomInbox).filter(f => f.endsWith('.json'));
      const messages: PendingMessage[] = [];

      for (const file of files) {
        const filePath = join(this.warRoomInbox, file);
        try {
          const content = readFileSync(filePath, 'utf8');
          const msg = JSON.parse(content);
          messages.push({
            ...msg,
            file_path: filePath
          });
        } catch (e) {
          console.error(`Error reading message file ${filePath}:`, e);
        }
      }

      // Sort by timestamp (oldest first)
      return messages.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
    } catch (e) {
      // Directory might not exist yet if no messages received
      return [];
    }
  }

  public evaluateAction(message: PendingMessage): { mode: ApprovalMode, trigger?: string, description?: string } {
    // 1. Check escalation triggers based on payload heuristics
    
    // Example: invoice_over_500
    if (message.message_type === 'deliverable' && message.payload && message.payload.type === 'invoice') {
      const amount = message.payload.amount || 0;
      if (amount > 500) {
        const rule = this.escalationRules.find(r => r.trigger === 'invoice_over_500');
        if (rule) {
          return { mode: rule.action, trigger: rule.trigger, description: rule.description };
        }
      }
    }

    // Handle tool proposals based on evolution config
    if (message.message_type === 'tool_proposal') {
      let requireApproval = false;
      try {
        const configPath = join(process.cwd(), 'milimo-blueprint', 'evolution_config.yaml');
        const content = readFileSync(configPath, 'utf8');
        const config = yamlParse(content);
        if (config && config.deployment && typeof config.deployment.require_proposal_approval === 'boolean') {
          requireApproval = config.deployment.require_proposal_approval;
        }
      } catch (e) {
        // Default to false if config not found
      }
      return requireApproval ? { mode: 'REVIEW', description: 'Tool proposal review' } : { mode: 'AUTO' };
    }

    // Default modes based on needs_approval flag from Contracts
    if (message.needs_approval) {
      return { mode: 'REVIEW' };
    }
    
    return { mode: 'AUTO' };
  }

  public processDecision(message: PendingMessage, decision: 'APPROVED' | 'REJECTED' | 'DELEGATED', operatorId: string = 'system', reason?: string) {
    this.audit.logAction({
      messageId: message.message_id,
      clawRole: message.sender_role,
      actionType: `WAR_ROOM_${decision}`,
      decision,
      operatorId,
      reason,
      details: {
        message_type: message.message_type,
        recipient: message.recipient_role
      }
    });

    if (decision === 'APPROVED') {
      // Move from war_room inbox to actual recipient inbox
      const targetInbox = join(this.meshDir, 'inbox', message.recipient_role);
      const fileName = message.file_path.split('/').pop()!;
      const targetPath = join(targetInbox, fileName);
      
      try {
        renameSync(message.file_path, targetPath);
      } catch (e) {
        console.error(`Failed to route approved message ${message.message_id}:`, e);
      }
    } else if (decision === 'REJECTED') {
      // Move to rejected queue
      const rejectedDir = join(this.meshDir, 'rejected');
      const fileName = message.file_path.split('/').pop()!;
      const targetPath = join(rejectedDir, fileName);
      
      try {
        renameSync(message.file_path, targetPath);
      } catch (e) {
        console.error(`Failed to move rejected message ${message.message_id}:`, e);
      }
    } else if (decision === 'DELEGATED') {
      // Leave it in the queue, perhaps tag it somehow in future
      // For now, no file move is strictly needed for HOLD
    }
  }

  public autoProcessEligible() {
    const pending = this.getPendingMessages();
    for (const msg of pending) {
      const evaluation = this.evaluateAction(msg);
      if (evaluation.mode === 'AUTO') {
        // Check rate limit before auto-approving
        if (this.rateLimiter) {
          const rateResult = this.rateLimiter.tryConsume();
          if (!rateResult.allowed) {
            console.log(
              `Rate limit reached for auto-approval. Message ${msg.message_id} requires manual review.`
            );
            this.audit.logAction({
              messageId: msg.message_id,
              clawRole: msg.sender_role,
              actionType: 'RATE_LIMITED',
              decision: 'DELEGATED',
              operatorId: 'rate-limiter',
              reason: rateResult.reason || 'Daily auto-approval limit exceeded',
              details: {
                remaining: rateResult.remaining,
                resetAt: rateResult.resetAt,
              },
            });
            continue; // Skip to next message, leave this for manual review
          }
        }

        this.processDecision(msg, 'APPROVED', 'auto-engine', 'Auto-approved per policy');
      }
    }
  }

  /**
   * Get rate limiter status for display in War Room.
   */
  public getRateLimitStatus(): {
    tier: string;
    dailyRemaining: number;
    dailyLimit: number;
    burstRemaining: number;
    burstLimit: number;
    dailyResetAt: string;
    burstResetAt: string;
  } | null {
    if (!this.rateLimiter) {
      return null;
    }
    const status = this.rateLimiter.getStatus();
    return {
      tier: status.tier,
      dailyRemaining: status.dailyRemaining,
      dailyLimit: status.dailyLimit,
      burstRemaining: status.burstRemaining,
      burstLimit: status.burstLimit,
      dailyResetAt: status.dailyResetAt,
      burstResetAt: status.burstResetAt,
    };
  }
}
