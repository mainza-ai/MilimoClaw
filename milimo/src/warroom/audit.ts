import { writeFileSync, existsSync, mkdirSync, readFileSync, appendFileSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';

export interface AuditEntry {
  timestamp: string;
  messageId?: string;
  clawRole?: string;
  actionType: string;
  decision?: 'APPROVED' | 'REJECTED' | 'DELEGATED' | 'AUTO';
  operatorId?: string;
  reason?: string;
  details?: Record<string, any>;
}

export class AuditLogger {
  private auditDir: string;
  private auditFile: string;

  constructor(squadId: string) {
    const home = process.env.HOME || process.env.USERPROFILE || homedir() || '/tmp';
    this.auditDir = join(home, '.milimo', 'audit', squadId);
    this.auditFile = join(this.auditDir, 'audit.jsonl');
    this.ensureDirectory();
  }

  private ensureDirectory() {
    if (!existsSync(this.auditDir)) {
      mkdirSync(this.auditDir, { recursive: true });
    }
  }

  public logAction(entry: Omit<AuditEntry, 'timestamp'>) {
    const fullEntry: AuditEntry = {
      timestamp: new Date().toISOString(),
      ...entry,
    };
    
    // Append as a single line JSON (JSONL format)
    appendFileSync(this.auditFile, JSON.stringify(fullEntry) + '\n', 'utf8');
  }

  public getRecentLogs(limit: number = 50): AuditEntry[] {
    if (!existsSync(this.auditFile)) {
      return [];
    }

    try {
      const content = readFileSync(this.auditFile, 'utf8');
      const lines = content.split('\n').filter(line => line.trim() !== '');
      
      // Get the last `limit` lines
      const recentLines = lines.slice(-limit);
      
      return recentLines.map(line => JSON.parse(line) as AuditEntry);
    } catch (e) {
      console.error('Failed to read audit log:', e);
      return [];
    }
  }
}
