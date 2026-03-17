import { describe, it } from 'node:test';
import * as assert from 'node:assert';
import { AuditLogger } from '../milimo/dist/warroom/audit.js';
import { existsSync, readFileSync, rmSync, mkdirSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';

describe('AuditLogger', () => {
  const squadId = 'test-squad';
  const home = process.env.HOME || process.env.USERPROFILE || homedir() || '/tmp';
  const testDir = join(home, '.milimo', 'audit', squadId);
  const testFile = join(testDir, 'audit.jsonl');

  it('initializes audit directory and file', () => {
    if (existsSync(testDir)) {
      rmSync(testDir, { recursive: true, force: true });
    }
    
    const logger = new AuditLogger(squadId);
    logger.logAction({ actionType: 'START' });

    assert.ok(existsSync(testFile), 'Audit file should exist');
  });

  it('logs actions correctly and retrieves them', () => {
    const logger = new AuditLogger(squadId);
    
    logger.logAction({
      actionType: 'WAR_ROOM_APPROVED',
      clawRole: 'ops',
      decision: 'APPROVED',
      operatorId: 'unit-tester'
    });

    const logs = logger.getRecentLogs(2);
    assert.ok(logs.length > 0);
    const lastLog = logs[logs.length - 1];
    assert.strictEqual(lastLog.actionType, 'WAR_ROOM_APPROVED');
    assert.strictEqual(lastLog.operatorId, 'unit-tester');
  });

  it('gets recent logs with limit', () => {
    const logger = new AuditLogger(squadId);
    
    for (let i = 0; i < 5; i++) {
        logger.logAction({ actionType: `TEST_ACTION_${i}` });
    }

    const limitedLogs = logger.getRecentLogs(3);
    assert.strictEqual(limitedLogs.length, 3);
    assert.strictEqual(limitedLogs[2].actionType, 'TEST_ACTION_4');
  });
});
