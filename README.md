# Annual Leave Tracker with MongoDB Integration

A Streamlit application for tracking and managing annual leave requests with persistent data storage using MongoDB Atlas.

## Features
- User registration and login system
- Add and manage leave requests
- Track remaining leave balance
- View leave history
- Custom working hours settings
- Persistent data storage with MongoDB Atlas

## Requirements
- Python 3.10+
- Streamlit
- PyMongo
- DNSPython

## Installation
```bash
pip install -r requirements.txt
```

## MongoDB Atlas Setup
1. Create a free MongoDB Atlas account at https://www.mongodb.com/cloud/atlas/register
2. Create a new cluster (the free tier is sufficient)
3. Create a database user with read/write permissions
4. Add your IP address to the IP access list
5. Get your connection string from the "Connect" button
6. Replace the placeholder in `.streamlit/secrets.toml` with your actual connection string

## Usage
```bash
streamlit run app.py
```
