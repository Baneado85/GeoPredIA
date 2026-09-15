namespace geopredia;

entity Zones {
  key ID          : UUID;
      name        : String(100);
      region      : String(100);
      latitude    : Decimal(9,6);
      longitude   : Decimal(9,6);
      evaluations : Association to many Evaluations on evaluations.zone = $self;
}

entity Evaluations {
  key ID               : UUID;
      zone             : Association to Zones;
      scenarioName     : String(50);
      modelVersion     : String(20);
      geoScore         : Decimal(5,2);
      envScore         : Decimal(5,2);
      socScore         : Decimal(5,2);
      globalRiskScore  : Decimal(5,2);
      status           : String(30);
      reviewerNotes    : String;
      evaluatedAt      : Timestamp;
}

entity IoTReadings {
  key ID          : UUID;
      deviceId    : String(50);
      zoneId      : String(36);
      sensorType  : String(50);
      value       : Decimal(10,4);
      unit        : String(20);
      isSimulated : Boolean;
      readingAt   : Timestamp;
}
