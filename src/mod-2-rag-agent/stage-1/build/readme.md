# Railway Deployment
This project is deployed on Railway for easy management and scalability.

### build locally
```shell
docker compose up -d
```

### install railway cli
```shell
curl -fsSL https://railway.com/install.sh | sh
railway login
```

### link project
```shell
railway link -p 82e5f3ba-db1b-455d-841a-5a2245e180ca
```

### redeploy
```shell
requirements.txt
railway up -d
```