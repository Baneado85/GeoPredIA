'use strict';

const cds = require('@sap/cds');

module.exports = class GeoPredIAService extends cds.ApplicationService {
  async init() {
    const { OfficialEvaluations, RiskScores, ReviewRequests, IoTReadings } = this.entities;

    this.before(['CREATE', 'UPDATE'], RiskScores, req => {
      const values = ['geological', 'environmental', 'social', 'globalRisk'];
      for (const name of values) {
        const value = req.data[name];
        if (value != null && (Number(value) < 0 || Number(value) > 100)) {
          req.reject(422, `${name} debe estar entre 0 y 100`);
        }
      }
      if (req.data.globalRisk != null && values.slice(0, 3).some(name => req.data[name] == null)) {
        req.reject(422, 'El riesgo global requiere las tres dimensiones');
      }
    });

    this.before('CREATE', IoTReadings, req => {
      for (const name of ['airHumidityPct', 'soilMoisturePct']) {
        const value = req.data[name];
        if (value != null && (Number(value) < 0 || Number(value) > 100)) {
          req.reject(422, `${name} debe estar entre 0 y 100`);
        }
      }
    });

    this.on('health', async () => {
      const datasetRows = await SELECT.one.from(OfficialEvaluations).columns('count(*) as count');
      const zones = await SELECT.from(OfficialEvaluations).columns('ZONA_ID').groupBy('ZONA_ID');
      return {
        service: 'GeoPredIA CAP',
        database: cds.env.requires.db?.kind || 'unknown',
        datasetRows: Number(datasetRows?.count || 0),
        distinctZones: zones.length,
        bpaConfigured: Boolean(process.env.BPA_API_URL && process.env.BPA_DEFINITION_ID)
      };
    });

    this.on('submitForReview', async req => {
      const { evaluationId, zoneId } = req.data;
      if (!evaluationId || !zoneId) req.reject(400, 'evaluationId y zoneId son obligatorios');
      const exists = await SELECT.one.from(RiskScores).where({ evaluationId, zoneId });
      if (!exists) req.reject(404, 'No existe el scoring solicitado');
      const duplicate = await SELECT.one.from(ReviewRequests).where({ evaluationId });
      if (duplicate) req.reject(409, 'La evaluación ya fue enviada a revisión');

      const record = {
        ID: cds.utils.uuid(), evaluationId, zoneId,
        status: process.env.BPA_API_URL ? 'READY_FOR_BPA' : 'PENDING_LOCAL'
      };
      await INSERT.into(ReviewRequests).entries(record);
      return SELECT.one.from(ReviewRequests).where({ ID: record.ID });
    });

    return super.init();
  }
};
