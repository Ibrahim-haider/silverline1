# RD Silver Line Partner Portal

A Streamlit prototype for managing RD Electronics' Silver Line referral partner program.

## Features
- Register Silver Line partners
- Auto-generate partner codes
- Add referrals and leads
- Track closed sales
- Calculate Rs. 1,000 commission per closed sale
- View dashboard KPIs
- Export partner, referral and commission reports

## How to Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Default Commission Logic
Commission is fixed at Rs. 1,000 when sale status is "Closed Sale".
