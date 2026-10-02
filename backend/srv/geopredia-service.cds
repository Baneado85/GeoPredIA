using { geopredia as db } from '../db/schema';

@path: '/odata/v4/geopredia'
service GeoPredIAService {
  @readonly entity OfficialEvaluations as projection on db.OfficialEvaluations;
  entity RiskScores as projection on db.RiskScores;
  entity ReviewRequests as projection on db.ReviewRequests;
  entity IoTReadings as projection on db.IoTReadings;

  type Status {
    service       : String;
    database      : String;
    datasetRows   : Integer;
    distinctZones : Integer;
    bpaConfigured : Boolean;
  }

  function health() returns Status;
  action submitForReview(evaluationId: String(64), zoneId: String(20)) returns ReviewRequests;
}
