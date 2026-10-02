'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const cds = require('@sap/cds');

test('CAP model exposes the official dataset and integration entities', async () => {
  const model = await cds.load(['db', 'srv']);
  const definitions = model.definitions;
  assert.ok(definitions['geopredia.OfficialEvaluations']);
  assert.ok(definitions['GeoPredIAService.OfficialEvaluations']);
  assert.ok(definitions['GeoPredIAService.RiskScores']);
  assert.ok(definitions['GeoPredIAService.ReviewRequests']);
  assert.ok(definitions['GeoPredIAService.IoTReadings']);
  assert.equal(definitions['geopredia.OfficialEvaluations'].elements.EVALUACION_ID.key, true);
});

test('health and review actions are part of the OData contract', async () => {
  const model = await cds.load(['db', 'srv']);
  const health = model.definitions['GeoPredIAService.health'];
  const submit = model.definitions['GeoPredIAService.submitForReview'];
  assert.equal(health.kind, 'function');
  assert.equal(submit.kind, 'action');
  assert.ok(submit.params.evaluationId);
  assert.ok(submit.params.zoneId);
});
