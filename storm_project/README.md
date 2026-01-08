# Storm Tracking (Group 02) - DSA3101 AY25/26 Sem 1

## About the Project
Storm tracking has been widely used across the world to monitor severe weather events by major weather agencies such as the National Oceanic and Atmospheric Administration (NOAA) and the National Hurricane Agency in the USA. In Singapore, the National Environmental Agency (NEA) has traditionally relied on radar imagery and ground-based weather stations to monitor storms in real time. However, no database tracking storms over time is currently available.

This project was developed to create such a database, and to test the hypothesis that storms in Singapore have become more frequent and more severe in recent years. By systematically tracking and analysing storm cells, using the radar images and weather data available to us, we aim to quantify changes in storm intensity and duration across time within Singapore. We hope to better observe these historical trends, and help improve existing local weather forecast algorithms to improve preparedness for future severe storm events.

For more information, check out our wiki.

## Getting started
To get the project running, follow these steps:

### Prerequisites
- Ensure that you have Docker installed, and the Docker daemon running on your machine. Check out https://www.docker.com/get-started/ for more information on how to do so.
- Sign in to our cloud SQL storage (DSA3101 Stormers) via Google Cloud Services. If you are unable to access it, please contact @nitzlodean.
  https://console.cloud.google.com/welcome?project=vigilant-cider-474204-j7

### 1. Clone this repository
```
git clone https://github.com/robinlogic/storm-tracking-dashboard-project-dsa3101.git
```

### 2. Navigate to the project directory
Replace the path name with the path to the folder where the repository was cloned.
```
cd path/storm_project
```

### 3. Turn on the cloud instance
- Open "DSA3101 Stormers" Project on Google Cloud Services
- Navigate to side bar > Cloud SQL > turn on Instance. **Turn it off immediately after you are done.**

### 4. Build and run the containers from path/storm_project/
```
docker compose up --build
```

### 5. Access the web-app on https://localhost:8050/ or https://127.0.0.1:8050/
- Use any browser to access the URLs

### 6. After using the website
- Return to the terminal/command prompt window where the Docker container was started from
- Press `Ctrl + C` to terminate the process
- Run
```
docker compose down
```

### 7. End of session

