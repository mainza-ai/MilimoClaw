import { describe, it } from 'node:test';
import * as assert from 'node:assert';
import { ApprovalEngine } from '../milimo/dist/warroom/approval.js';

describe('ApprovalEngine', () => {
  const squadId = 'test-squad';

  it('evaluates normal message as REVIEW or AUTO', () => {
    // Engine initializes with default VETO for invoice_over_500 if mesh_config.yaml is not found or loaded minimally
    const engine = new ApprovalEngine(squadId);

    const normalMsg = {
      message_id: 'msg-1',
      sender_role: 'ops',
      recipient_role: 'content',
      message_type: 'brief',
      payload: { project: 'test' },
      squad_id: squadId,
      timestamp: new Date().toISOString(),
      needs_approval: false,
      file_path: '/fake/path.json'
    };

    const evalRes = engine.evaluateAction(normalMsg);
    assert.strictEqual(evalRes.mode, 'AUTO');

    const reviewMsg = { ...normalMsg, needs_approval: true };
    const revRes = engine.evaluateAction(reviewMsg);
    assert.strictEqual(revRes.mode, 'REVIEW');
  });

  it('evaluates escalation matching invoice_over_500 as VETO', () => {
    const engine = new ApprovalEngine(squadId);

    const invoiceMsg = {
      message_id: 'msg-invoice-1',
      sender_role: 'finance',
      recipient_role: 'war_room',
      message_type: 'deliverable',
      payload: { type: 'invoice', amount: 600 },
      squad_id: squadId,
      timestamp: new Date().toISOString(),
      needs_approval: true,
      file_path: '/fake/invoice.json'
    };

    const evalRes = engine.evaluateAction(invoiceMsg);
    assert.strictEqual(evalRes.mode, 'VETO');
    assert.strictEqual(evalRes.trigger, 'invoice_over_500');
  });
});
