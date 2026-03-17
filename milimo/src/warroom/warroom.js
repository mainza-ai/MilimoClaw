"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.WarRoomTUI = void 0;
var readline = require("readline");
var approval_1 = require("./approval");
var audit_1 = require("./audit");
var WarRoomTUI = /** @class */ (function () {
    function WarRoomTUI(squadId, operatorId) {
        if (operatorId === void 0) { operatorId = 'local-operator'; }
        this.squadId = squadId;
        this.operatorId = operatorId;
        this.isRunning = false;
        this.refreshInterval = null;
        this.pendingQueue = [];
        this.engine = new approval_1.ApprovalEngine(squadId);
        this.audit = new audit_1.AuditLogger(squadId);
        this.rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout
        });
    }
    WarRoomTUI.prototype.start = function () {
        var _this = this;
        this.isRunning = true;
        console.clear();
        console.log('--- MILIMO CLAW: WAR ROOM ---');
        console.log("Squad: ".concat(this.squadId, " | Operator: ").concat(this.operatorId));
        console.log('Type "help" for commands, "exit" to leave.\n');
        // Initial load
        this.refreshQueue();
        this.displayPrompt();
        // Background poll for new messages
        this.refreshInterval = setInterval(function () {
            var oldLen = _this.pendingQueue.length;
            _this.refreshQueue();
            if (_this.pendingQueue.length > oldLen) {
                process.stdout.write("\n[ALERT] New pending action arrived. (".concat(_this.pendingQueue.length, " total)\nmilimo> "));
            }
        }, 5000);
        this.rl.on('line', function (line) {
            _this.handleCommand(line.trim());
        });
    };
    WarRoomTUI.prototype.stop = function () {
        this.isRunning = false;
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        this.rl.close();
        console.log('\nExiting War Room. Claws will continue operating.');
    };
    WarRoomTUI.prototype.refreshQueue = function () {
        this.pendingQueue = this.engine.getPendingMessages();
    };
    WarRoomTUI.prototype.displayPrompt = function () {
        if (!this.isRunning)
            return;
        this.rl.setPrompt('milimo> ');
        this.rl.prompt();
    };
    WarRoomTUI.prototype.handleCommand = function (cmd) {
        var parts = cmd.split(' ');
        var action = parts[0].toLowerCase();
        switch (action) {
            case 'help':
                console.log("\nCommands:\n  ls          - List pending actions in queue\n  view <id>   - View details of a pending action\n  approve <id>- Approve an action (sends to recipient)\n  veto <id>   - Reject an action (moves to rejected)\n  hold <id>   - Defer an action (leaves in queue)\n  feed        - View recent audit trail\n  exit        - Leave the War Room\n");
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
                console.log("Unknown command: ".concat(action));
        }
        this.displayPrompt();
    };
    WarRoomTUI.prototype.listPending = function () {
        var _this = this;
        this.refreshQueue();
        if (this.pendingQueue.length === 0) {
            console.log('No pending actions in queue.');
            return;
        }
        console.log("\nPENDING ACTIONS (".concat(this.pendingQueue.length, "):"));
        this.pendingQueue.forEach(function (msg) {
            var evalResult = _this.engine.evaluateAction(msg);
            var modeTag = "[".concat(evalResult.mode, "]");
            if (evalResult.trigger) {
                modeTag += "[".concat(evalResult.trigger, "]");
            }
            console.log("".concat(msg.message_id, " | ").concat(msg.sender_role, " -> ").concat(msg.recipient_role, " | ").concat(msg.message_type, " ").concat(modeTag));
        });
        console.log('');
    };
    WarRoomTUI.prototype.viewAction = function (id) {
        if (!id) {
            console.log('Usage: view <id>');
            return;
        }
        var msg = this.pendingQueue.find(function (m) { return m.message_id === id; });
        if (!msg) {
            console.log("Action ".concat(id, " not found pending queue."));
            return;
        }
        console.log("\n--- Action ".concat(id, " ---"));
        console.log("Time: ".concat(msg.timestamp));
        console.log("Route: ".concat(msg.sender_role, " -> ").concat(msg.recipient_role));
        console.log("Type: ".concat(msg.message_type));
        console.log("Payload:");
        console.log(JSON.stringify(msg.payload, null, 2));
        var evalResult = this.engine.evaluateAction(msg);
        if (evalResult.description) {
            console.log("Notice: ".concat(evalResult.description));
        }
        console.log('------------------\n');
    };
    WarRoomTUI.prototype.processAction = function (id, decision) {
        if (!id) {
            console.log("Usage: ".concat(decision.toLowerCase(), " <id>"));
            return;
        }
        var msg = this.pendingQueue.find(function (m) { return m.message_id === id; });
        if (!msg) {
            console.log("Action ".concat(id, " not found in pending queue."));
            return;
        }
        this.engine.processDecision(msg, decision, this.operatorId);
        console.log("Action ".concat(id, " marked as ").concat(decision, "."));
        this.refreshQueue();
    };
    WarRoomTUI.prototype.showFeed = function () {
        var logs = this.audit.getRecentLogs(10);
        if (logs.length === 0) {
            console.log('Audit trail is empty.');
            return;
        }
        console.log('\n--- Recent Activity Feed ---');
        logs.forEach(function (log) {
            var roleBlock = log.clawRole ? "[".concat(log.clawRole, "] ") : '';
            var decisionBlock = log.decision ? " -> ".concat(log.decision) : '';
            console.log("".concat(log.timestamp, " | ").concat(roleBlock).concat(log.actionType).concat(decisionBlock, " (Op: ").concat(log.operatorId || 'system', ")"));
        });
        console.log('----------------------------\n');
    };
    return WarRoomTUI;
}());
exports.WarRoomTUI = WarRoomTUI;
