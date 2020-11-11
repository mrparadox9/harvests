# harvests
you need a .env file in the same directory as Dockerfile with the following entries:
ACCOUNT_ADDRESS=<wallet address that staked drugs/has LP>
ACCOUNT_PRIVATE_KEY=<private key for the above>

run with:
docker build -t <image name> .
docker run --env-file .env <image name>

