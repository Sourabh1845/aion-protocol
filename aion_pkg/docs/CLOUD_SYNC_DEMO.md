# AION Cloud Sync Demo

Stage 5 MVP connects local AION receipts to AION Cloud.

## Flow

1. Register on AION Cloud and get an API key.
2. Set local environment variable:

AION_CLOUD_API_KEY=your-api-key

3. Generate a local receipt:

aion guard-demo

4. Upload latest receipt:

aion cloud-sync

5. Verify in cloud:

GET https://aion-cloud.onrender.com/receipts?limit=3

## Current Status

Working:

- AION Cloud register
- Cloud receipt storage
- Cloud receipt listing
- Local AION cloud-sync
- Neon Postgres
- Render deployment

Not included yet:

- full dashboard receipt UI
- billing
- team accounts
- Slack/webhook approval flows
