const fs = require('fs');
const pemJwk = require('pem-jwk');

// Read the public key
const publicKeyPem = fs.readFileSync('epic_public_key.pem', 'utf8');

// Convert to JWK
const jwk = pemJwk.pem2jwk(publicKeyPem);

// Add necessary fields for JWKS
jwk.kid = 'atlas-key-001';  // Key ID
jwk.use = 'sig';            // Key usage
jwk.alg = 'RS384';          // Algorithm

// Create JWKS structure
const jwks = {
  keys: [jwk]
};

// Write to file
fs.writeFileSync('.well-known/jwks.json', JSON.stringify(jwks, null, 2));
console.log('JWKS file created successfully in .well-known/jwks.json'); 