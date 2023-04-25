# AdminCoder

Geocoding app for administrative boundary units


# Debugging

To simulate and debug the deployment environment during local testing: 

1. Download and install podman. 
2. Cd into the repository. 
3. Start a podman linux machine: `podman machine init`.
4. Run `podman --log-level debug build . --ignorefile .dockerignore --tag localtest` will build an image based on `Dockerfile`, the same one used for production. 
5. Run `podman run -p 8000:8000 --env-file .env localtest` to run a container of the image along with an env file. 
6. Go to `localhost:8000` in a browser to test the site. 

This should produce a replica of what will happen in production. 
