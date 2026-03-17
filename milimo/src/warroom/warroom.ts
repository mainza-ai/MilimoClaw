import * as readline from 'readline';
import { ApprovalEngine, PendingMessage } from './approval';
import { AuditLogger } from './audit';

export class WarRoomTUI {
  private rl: readline.Interface;
  private engine: ApprovalEngine;
  private audit: AuditLogger;
  private isRunning: boolean = false;
  private refreshInterval: NodeJS.Timeout | null = null;
  private pendingQueue: PendingMessage[] = [];
  
  constructor(private squadId: string, private operatorId: string = 'local-operator') {
    this.engine = new ApprovalEngine(squadId);
    this.audit = new AuditLogger(squadId);
    
    this.rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });
  }

  public start() {
    this.isRunning = true;
    console.clear();
    console.log('--- MILIMO CLAW: WAR ROOM ---');
    console.log(`Squad: ${this.squadId} | Operator: ${this.operatorId}`);
    console.log('Type "help" for commands, "exit" to leave.\n');

    // Initial load
    this.refreshQueue();
    this.displayPrompt();

    // Background poll for new messages
    this.refreshInterval = setInterval(() => {
      const oldLen = this.pendingQueue.length;
      this.refreshQueue();
      if (this.pendingQueue.length > oldLen) {
        process.stdout.write(`\n[ALERT] New pending action arrived. (${this.pendingQueue.length} total)\nmilimo> `);
      }
    }, 5000);

    this.rl.on('line', (line) => {
      this.handleCommand(line.trim());
    });
  }

  public stop() {
    this.isRunning = false;
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
    this.rl.close();
    console.log('\nExiting War Room. Claws will continue operating.');
  }

  private refreshQueue() {
    this.pendingQueue = this.engine.getPendingMessages();
  }

  private displayPrompt() {
    if (!this.isRunning) return;
    this.rl.setPrompt('milimo> ');
    this.rl.prompt();
  }

  private handleCommand(cmd: string) {
    const parts = cmd.split(' ');
    const action = parts[0].toLowerCase();

    switch (action) {
      case 'help':
        console.log(`
Commands:
  ls          - List pending actions in queue
  view <id>   - View details of a pending action
  approve <id>- Approve an action (sends to recipient)
  veto <id>   - Reject an action (moves to rejected)
  hold <id>   - Defer an action (leaves in queue)
  feed        - View recent audit trail
  exit        - Leave the War Room
`);
        break;
      
      case 'ls':
        this.listPending();
        break;
      
      case 'view':
        this.viewAction(parts[1]);
        break;
      
      case 'approve':
        this.processAction(parts[1], 'APPROVED');
        break;
      
      case 'veto':
        this.processAction(parts[1], 'REJECTED');
        break;

      case 'hold':
        this.processAction(parts[1], 'DELEGATED');
        break;

      case 'feed':
        this.showFeed();
        break;

      case 'exit':
      case 'quit':
        this.stop();
        return;
      
      case '':
        break;

      default:
        console.log(`Unknown command: ${action}`);
    }

    this.displayPrompt();
  }

  private listPending() {
    this.refreshQueue();
    if (this.pendingQueue.length === 0) {
      console.log('No pending actions in queue.');
      return;
    }

    console.log(`\nPENDING ACTIONS (${this.pendingQueue.length}):`);
    this.pendingQueue.forEach(msg => {
      const evalResult = this.engine.evaluateAction(msg);
      let modeTag = `[${evalResult.mode}]`;
      if (evalResult.trigger) {
        modeTag += `[${evalResult.trigger}]`;
      }
      console.log(`${msg.message_id} | ${msg.sender_role} -> ${msg.recipient_role} | ${msg.message_type} ${modeTag}`);
    });
    console.log('');
  }

  private viewAction(id: string) {
    if (!id) {
      console.log('Usage: view <id>');
      return;
    }
    const msg = this.pendingQueue.find(m => m.message_id === id);
    if (!msg) {
      console.log(`Action ${id} not found pending queue.`);
      return;
    }

    console.log(`\n--- Action ${id} ---`);
    console.log(`Time: ${msg.timestamp}`);
    console.log(`Route: ${msg.sender_role} -> ${msg.recipient_role}`);
    console.log(`Type: ${msg.message_type}`);
    console.log(`Payload:`);
    console.log(JSON.stringify(msg.payload, null, 2));
    
    const evalResult = this.engine.evaluateAction(msg);
    if (evalResult.description) {
      console.log(`Notice: ${evalResult.description}`);
    }
    console.log('------------------\n');
  }

  private processAction(id: string, decision: 'APPROVED' | 'REJECTED' | 'DELEGATED') {
    if (!id) {
      console.log(`Usage: ${decision.toLowerCase()} <id>`);
      return;
    }
    const msg = this.pendingQueue.find(m => m.message_id === id);
    if (!msg) {
      console.log(`Action ${id} not found in pending queue.`);
      return;
    }

    this.engine.processDecision(msg, decision, this.operatorId);
    console.log(`Action ${id} marked as ${decision}.`);
    this.refreshQueue();
  }

  private showFeed() {
    const logs = this.audit.getRecentLogs(10);
    if (logs.length === 0) {
      console.log('Audit trail is empty.');
      return;
    }

    console.log('\n--- Recent Activity Feed ---');
    logs.forEach(log => {
      const roleBlock = log.clawRole ? `[${log.clawRole}] ` : '';
      const decisionBlock = log.decision ? ` -> ${log.decision}` : '';
      console.log(`${log.timestamp} | ${roleBlock}${log.actionType}${decisionBlock} (Op: ${log.operatorId || 'system'})`);
    });
    console.log('----------------------------\n');
  }
}
