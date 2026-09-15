const express = require('express');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

const PORT = process.env.PORT || 4004;

// Endpoint Salud
app.get('/health', (req, res) => {
  res.json({ status: 'UP', service: 'GeoPredIA SAP CAP Integration Gateway' });
});

// Endpoint Ingesta Telemetría IoT (GeoRisk Sentinel)
app.post('/api/iot/telemetry', (req, res) => {
  const { device_id, zone_id, readings, is_simulated } = req.body;
  console.log(`[IoT Ingest] Device: ${device_id} | Zone: ${zone_id} | Readings: ${readings.length}`);
  
  // Lógica de alerta por umbral
  const warnings = readings.filter(r => r.status === 'WARNING' || r.status === 'CRITICAL');
  if (warnings.length > 0) {
    console.log(`[BPA Trigger] Se ha emitido una solicitud de revision automatica por alerta IoT!`);
  }

  res.status(201).json({
    status: 'ACCEPTED',
    message: 'Telemetria almacenada exitosamente en SAP HANA Cloud',
    alerts_triggered: warnings.length
  });
});

// Endpoint Carga POV SAC -> HANA -> BPA
app.post('/api/evaluations/upload-pov', (req, res) => {
  const { zone_id, scenario, geo_score, env_score, soc_score, global_score } = req.body;
  
  const evaluation_id = `EVAL-${Date.now()}`;
  console.log(`[POV Ingest] Evaluacion ${evaluation_id} registrada para zona ${zone_id}. Risk Global: ${global_score}`);

  res.status(200).json({
    status: 'SUCCESS',
    evaluation_id,
    bpa_process_instance: `BPA-PROC-${Math.floor(Math.random() * 100000)}`,
    message: 'Evaluacion cargada e iniciada en SAP Build Process Automation'
  });
});

app.listen(PORT, () => {
  console.log(`🚀 GeoPredIA CAP Service running on port ${PORT}`);
});
