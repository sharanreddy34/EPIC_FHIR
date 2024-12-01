# Epic FHIR API Integration

This repository contains tools for authenticating with the Epic FHIR API using JWT.

## Setup

### 1. Files in this Repository
- `epic_private_key.pem` - Private RSA key for JWT signing
- `epic_public_key.pem` - Public RSA key to share with Epic
- `.well-known/jwks.json` - JSON Web Key Set file that needs to be hosted at a public URL
- `generate_epic_jwt.py` - Script to generate JWT tokens
- `get_epic_token.py` - Script to obtain access tokens from Epic

### 2. Host Your JWKS File
The `.well-known/jwks.json` file must be hosted at a publicly accessible URL. You can:
- Host it on GitHub Pages (your repository URL + `/.well-known/jwks.json`)
- Host it on your own web server
- Use a service like Netlify, Vercel, or AWS S3

### 3. Register Your App with Epic
You'll need to register your application with Epic to get a client ID:
1. Visit the Epic App Orchard (https://appmarket.epic.com/)
2. Create a developer account if you don't have one
3. Register a new application
4. Provide your JWKS URL during registration
5. Note your client ID for use in authentication

## Usage

### Generate a JWT Token

```bash
python generate_epic_jwt.py --key epic_private_key.pem --client-id YOUR_CLIENT_ID --jwks-url https://your-domain.com/.well-known/jwks.json
```

### Get an Access Token from Epic

```bash
python get_epic_token.py --key epic_private_key.pem --client-id YOUR_CLIENT_ID --jwks-url https://your-domain.com/.well-known/jwks.json --scope "system/Patient.read system/Appointment.read"
```

Or with an existing JWT:

```bash
python get_epic_token.py --jwt YOUR_JWT_TOKEN
```

### Save the Token to a File

```bash
python get_epic_token.py --key epic_private_key.pem --client-id YOUR_CLIENT_ID --output token.json
```

## Making API Requests

After obtaining an access token, you can make requests to the Epic FHIR API:

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/Patient/12345
```

## Important Notes

1. **Key Security**: Keep your private key secure and never share it.
2. **Scopes**: Request only the scopes your application needs.
3. **Token Expiration**: Tokens expire quickly (typically 5 minutes), so generate a new one for each session.
4. **Epic Documentation**: Refer to Epic's documentation for specific API endpoints and requirements.

## Troubleshooting

- **401 Unauthorized**: Check that your JWT is valid, not expired, and that the client ID is correct.
- **403 Forbidden**: Check that your requested scopes are authorized for your application.
- **Invalid Signature**: Ensure your JWKS URL is accessible and contains the correct public key.

For more help, refer to the [Epic API documentation](https://fhir.epic.com/Documentation). 