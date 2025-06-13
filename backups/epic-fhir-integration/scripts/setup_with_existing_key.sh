#!/bin/bash
# Set up JWT-based authentication for Epic FHIR API using an existing key
# This script uses the provided key.md content

set -e  # Exit on error

echo "Setting up JWT-based authentication using the provided private key"

# Create directories if they don't exist
mkdir -p auth/keys
mkdir -p fhir_pipeline/auth/keys

# Copy the key from key.md to the expected location
echo "Copying private key to auth/keys/rsa_private.pem"
cat > auth/keys/rsa_private.pem << 'EOF'
-----BEGIN PRIVATE KEY-----
MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQC+qJzRm3jRyxPC
vHqsZoRkalc8t5xzbwMPvgpzVxJcdTeTG+WhWPZwyxJHC7olYRFhy4vr3WVps3aw
iTZVpor422i7yPBaNBtVlnwMOf5z8u+plUPMWQ3cvbNcsgRFvd2HAZ96rgqnnfX1
jTvdmIt0zm2eg7d4w7SPUtCF8rhkpezG1zVkk8Z/Hk/Bg+Qy0izS+0teoZ8cv2ko
E3IQu9d9yq3yB9Ep0EpabrzdMnxyug8/aaqw6RIVUSuJ+Wau8Oy+dNbHxsrEd1oL
1LCIxkTEDyylygRDbdNH2imNsVnY81U4NjLUcJnyaubhiY0ldHUkOsN8bsIzuVYk
lUBJcoC1AgMBAAECggEACZjtQ/PikhT56qyYNEN42KEtwQWxH3JwIgO7/PBeIT9Z
S9N0rLmQtj7SrbbeaPFI8bZQVdAwQbDiAaL2lDss9bf9vq4vwyqqUZWgqvDkaSvK
eqvj3M6CzyDRfZIMewJCu4AOahuGt8dQ0UqJv+7k3j1h8T/KJY8ccLaHfqaoN5C4
X35ow8us2Q8EHHp5SuOiJ66h29PKxx9wFwSamYfqUGIcCN93RsvLgtAYl8EeVgBy
Ik3Fvlge/MqzQEJFXYTBelxUA61pw9O6sGZmK640XOVmTPsEsfOZBW86EjYIho/Y
Nik0mcBjJA4FLOKmNo4IUFxXY+MVNrQh54I6ZmUgoQKBgQDrwX76AIdDLQiwy1oP
yGjhRr5PZsTry8Dl2Sa0dArwiU1ske8JEUr20qO4OShDr7tILyPaM8yGEGmpzVNd
veFFCMru0+MjmatwT2Ogd9ixwrcXfmtPxlYtd59QoGdWNv0lcRKdceWFAmwY12tB
A3UN3/d0TXrgeqBViCmK8lwHKQKBgQDPB8Rio+EB59ySgd/RXHL92LCkjkbPLl5B
AM5Z9tJIKewcv/h9HVOPs0d0tKsn1fJGCRAwjC0goOcxbMInr/Iq68PzSCD/7A7X
VcVeb2ox/5PlenQ5pr2Om9TD3RARZi52tARoObodhEZpPtJlzWU5TCCQbTppYhT/
ZbP12ruarQKBgDkeKitb0WmfEYnz2qAUSAS8ZQNLvM38EYIeeFgj/TqFqXJycN1b
iTP/mJbbkjvD6bX1ZdRJ1HVuqIrxKg9+H4PgO3pdb5yCcJzHPzXzk1aN/Fn+0PUE
8oAViU25bw/eRrq5iG8I1zjAe3wRRPT9Z3CzIHrXArw8OXg/gwEc8trxAoGACW0p
G/SqQhP0jxcqwbWb5sL/B/8SakyKLhuDScVbPb3q6kQzZD75lwlqr32qbV3ochfn
jM5VH68z16REEtqIBDxH58PY/M4avuNA4VPhWfVxHnm84QMejme6AFEIckJcyzrX
GIfIWZ+0NQaPPeNkQH+e2/SdPD8jBZ3z27Xh5OECgYBo8jCxoOqBGcFFFE+ECkBm
eYDWpeWu0RWeqIn53uiamNNYGbgO0LLQcHtpP9pnWWBsFhhov71hCglvu2wSExRe
iXaAm/Pab+YgoRKoAM21v+06FTRwuPOm46xGJf6kujVWj4NaBfUmAjFgKwvUCAT9
Nr4Wj2BsK08U333VZvjLnA==
-----END PRIVATE KEY-----
EOF

# Create a symlink to the private key for the FHIR pipeline
echo "Creating symlink to private key in fhir_pipeline/auth/keys/"
ln -sf "../../../auth/keys/rsa_private.pem" "fhir_pipeline/auth/keys/rsa_private.pem"

# Get the client ID
read -p "Use production client ID? (y/n): " use_prod
if [ "$use_prod" = "y" ]; then
    client_id="43e4309a-67ab-4c3a-b583-f062c35d3791"
    environment="production"
else
    client_id="02317de4-f128-4607-989b-07892f678580"
    environment="non-production"
fi

# Create a .env file with the configuration
cat > .env << EOF
# Epic FHIR API Configuration
EPIC_CLIENT_ID=$client_id
EPIC_PRIVATE_KEY_PATH=auth/keys/rsa_private.pem
EPIC_ENVIRONMENT=$environment

# JWKS Configuration
EPIC_JWKS_URL=https://gsiegel14.github.io/ATLAS-EPIC/.well-known/jwks.json
EPIC_KEY_ID=atlas-key-001

# Pipeline Configuration
FHIR_DEBUG=true
EOF

echo "Created .env file with configuration"

# Add an entry to .gitignore to prevent committing private keys and tokens
if [ ! -f ".gitignore" ]; then
    touch .gitignore
fi

if ! grep -q "auth/keys/" .gitignore; then
    echo "auth/keys/" >> .gitignore
    echo "*.pem" >> .gitignore
    echo "epic_token.json" >> .gitignore
    echo ".env" >> .gitignore
    echo "Added private keys, tokens, and .env file to .gitignore"
fi

# Generate the public key from the private key
echo "Generating public key from private key"
openssl rsa -in auth/keys/rsa_private.pem -pubout -out auth/keys/rsa_public.pem

echo ""
echo "JWT Setup Complete!"
echo "----------------------------------------"
echo "To use JWT authentication for Epic FHIR API:"
echo ""
echo "1. Source the environment variables:"
echo "   source .env"
echo ""
echo "2. Run the FHIR pipeline with the test patient:"
echo "   ./run_with_patient.sh"
echo ""
echo "   Or run manually:"
echo "   python -m fhir_pipeline.cli extract --patient-id T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB --environment $environment --debug"
echo ""
echo "3. For more information, see the README.md"
echo "----------------------------------------" 