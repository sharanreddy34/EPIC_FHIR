
FHIR
API Specifications
Build Apps
Documentation 
Jump To 
Sign Up
Login 
OAuth 2.0 Specification
Per Breaking Change Notification Q-7365177, to enhance security in Epic back-end integrations, all apps that use backend OAuth 2.0 will soon be required to host their public keys at a JWK Set URL (JKU) instead of uploading a static key to each environment. This requirement does not apply to apps that do not have the "Backend Systems" user type. Refer to the following table for Epic versions when this requirement will take effect.

Epic Version

Epic Sandbox JKU Support

Epic Customer JKU Support

February 2025 and prior

Optional

Optional - Each customer can choose to enforce JKU support for backend OAuth apps. This enforcement is off by default.

August 2025

Vendor Services and Epic on FHIR no longer allow new static key uploads for use in the sandbox.

 
November 2025

Static keys no longer supported in the sandbox for backend OAuth.

Vendor Services and Epic on FHIR websites no longer allow static key uploads for new apps. Both sites still support rotating keys for live apps.

February 2026

Static keys are no longer supported in customer environments for backend OAuth.

Using OAuth 2.0
Applications must secure and protect the privacy of patients and their data. To help meet this objective, Epic supports using the OAuth 2.0 framework to authenticate and authorize applications.

Why OAuth 2.0?
OAuth 2.0 enables you to develop your application without having to build a credential management system. Instead of exposing login credentials to your application, your application and an EHR's authorization server exchange a series of authorization codes and access tokens. Your application can access protected patient data stored in an EHR's database after it obtains authorization from the EHR's authorization server.

Before You Get Started
To use OAuth 2.0 to authorize your application's access to patient information, some information needs to be shared between the authorization server and your application:

client_id: The client_id identifies your application to authentication servers within the Epic community and allows you to connect to any organization.
redirect_uri: The redirect_uri confirms your identity and is used to validate and redirect authentication requests that originate from your application. Epic's implementation allows for multiple redirect_uris.
Note that a redirect_uri is not needed for backend services using the client_credentials grant type.
An https protocol is required for use in a production environment, but http protocol-based redirect_uris are allowed for development and testing.
Registered redirect_uris must not contain anything in the fragment (i.e. anything after #).
Credentials: Some apps, sometimes referred to as confidential clients, can use credentials registered for a given EHR system to obtain authorization to access the system without a user or a patient implicitly or explicitly authorizing the app. Examples of this are apps that use refresh tokens to allow users to launch the app outside of an Epic client without needing to log in every time they use the app, and backend services that need to access resources without a specific person launching the app, for example, fetching data on a scheduled basis.
You can register your application for access to both the sandbox and Epic organizations here. You'll provide information to us, including one or more redirect_uris, and Epic will generate a client_id for you.

Apps can be launched from within an existing EHR or patient portal session, which is called an EHR launch. Alternatively, apps can be launched standalone from outside of an existing EHR session. Apps can also be backend services where no user is launching the app.

EHR launch (SMART on FHIR): The app is launched by the EHR calling a launch URL specified in the EHR's configuration. The EHR launches the launch URL and appends a launch token and the FHIR server's endpoint URL (ISS parameter) in the query string. The app exchanges the launch token, along with the client identification parameters to get an authorization code and eventually the access token.

See the Embedded Launch section of this guide for more details.
Standalone launch: The app launches directly to the authorize endpoint outside of an EHR session and requests context from the EHR's authorization server.

See the Standalone Launch section of this guide for more details.
Backend services: The app is not authorized by a specific person and likely does not have a user interface, and therefore calls EHR web services with system-level authorization.

See the Backend Services section of this guide for more details.
Desktop integrations through Subspace: The app requests access to APIs directly available on the EHR's desktop application via a local HTTP server.

See the Subspace Communication Framework specification for more details.
Starting in the August 2019 version of Epic, the Epic implementation of OAuth 2.0 supports PKCE and Epic recommends using PKCE for native mobile app integrations. For earlier versions or in cases where PKCE cannot be used, Epic recommends the use of Universal Links/App Links in lieu of custom redirect URL protocol schemes.


The app you build will list both a production Client ID and a non-production Client ID. While testing in the Epic on FHIR sandbox, use the non-production Client ID.

The base URL for the Current Sandbox environment is:

https://fhir.epic.com/interconnect-fhir-oauth/
EHR Launch (SMART on FHIR)
Contents

Step 1: Your Application is Launched from the Patient Portal or EHR
Step 2: Your Application Retrieves the Conformance Statement or SMART Configuration
Additional Header Requirements
Step 3: Your Application Requests an Authorization Code
Step 4: EHR's Authorization Server Reviews The Request
Step 5: Your Application Exchanges the Authorization Code for an Access Token
Non-confidential Clients
Frontend Confidential Clients
OpenID Connect id_tokens
Validating the OpenID Connect JSON Web Token
Step 6: Your Application Uses FHIR APIs to Access Patient Data
Step 7: Use a Refresh Token to Obtain a New Access Token
How It Works
The app is launched by the EHR calling a launch URL specified in the EHR's configuration. The EHR launches the launch URL and appends a launch token and the FHIR server's endpoint URL (ISS parameter) in the query string. The app exchanges the launch token, along with the client identification parameters to get an authorization code and eventually the access token.


Step 1: Your Application is Launched from the Patient Portal or EHR
Your app is launched by the EHR calling the launch URL which is specified in the EHR's configuration. The EHR sends a launch token and the FHIR server's endpoint URL (ISS parameter).

Note: If you are writing a web-based application that you intend to embed in Epic, you may find that your application may require minor modifications. We offer a simple testing harness to help you validate that your web application is compatible with the embeddable web application viewer in Epic. As embedding your application in Hyperspace may not behave the same as presenting it in a browser, ensure that your app works with the testing harness and that you can run multiple instances of the app at the same time within the same session.

launch: This parameter is an EHR generated token that signifies that an active EHR session already exists. This token is one-time use and will be exchanged for the authorization code.
See the Epic-Issued OAuth 2.0 Tokens appendix section for details on handling launch codes.
iss: This parameter contains the EHR's FHIR endpoint URL, which an app can use to find the EHR's authorization server.
Your application should create an allowlist of iss values (AKA resource servers) to protect against phishing attacks. Rather than accepting any iss value in your application, only accept those you know belong to the organizations you integrate with.
Step 2: Your Application Retrieves the Conformance Statement or SMART Configuration
To determine which authorize and token endpoints to use in the EHR launch flow, you should make a GET request to the metadata endpoint which is constructed by taking the iss provided and appending /metadata. Alternatively, when communicating with Epic organizations using the August 2021 version or Epic or later, you can make a GET request to the SMART configuration endpoint by taking the iss and appending /.well-known/smart-configuration.

If no Accept header is sent, the metadata response is XML-formatted and the smart-configuration response is JSON-formatted. An Accept header can be sent with a value of application/json, application/xml, and the metadata endpoint additionally supports application/fhir+json and application/json+fhir to specify the format of the response.

Metadata Example

Here's an example of what a full metadata request might look like.

GET https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/DSTU2/metadata HTTP/1.1
Accept: application/fhir+json
Here is an example of what the authorize and token endpoints would look like in the metadata response.

"extension": [
{
"url": "http://fhir-registry.smarthealthit.org/StructureDefinition/oauth-uris",
"extension": [
  {
    "url": "authorize",
    "valueUri": "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize"
  },
  {
    "url": "token",
    "valueUri": "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"
  }
]
}
]
Metadata Example with Dynamic Client Registration (starting in the November 2021 version of Epic)

Here's an example of what a full metadata request might look like. By including an Epic Client ID, clients authorized to perform dynamic client registration can then determine which endpoint to use when performing dynamic client registration. Note that this capability is only supported for STU3 and R4 requests.

GET https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/metadata HTTP/1.1
Accept: application/fhir+json
Epic-Client-ID: 0000-0000-0000-0000-0000
Here is an example of what the authorize, token, and dynamic registration endpoints would look like in the metadata response.

"extension": [
{
"url": "http://fhir-registry.smarthealthit.org/StructureDefinition/oauth-uris",
"extension": [
  {
    "url": "authorize",
    "valueUri": "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize"
  },
  {
    "url": "token",
    "valueUri": "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"
  },
  {
    "url": "register",
    "valueUri": https://fhir.epic.com/interconnect-fhir-oauth/oauth2/register
  }
]
}
]
Here's an example of what a smart-configuration request might look like.

GET https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/.well-known/smart-configuration HTTP/1.1
Accept: application/json
Here is an example of what the authorize and token endpoints would look like in the smart-configuration response.

"authorization_endpoint": "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize",
"token_endpoint": "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token",
"token_endpoint_auth_methods_supported": [
    "client_secret_post",
    "client_secret_basic",
    "private_key_jwt"
]
Retrieving Conformance Statement: Additional Header Requirements
In some cases when making your request to the metadata endpoint, you'll also need to include additional headers to ensure the correct token and authorize endpoints are returned. This is because in Epic, it is possible to configure the system such that the FHIR server's endpoint URL, provided in the iss parameter, is overridden on a per client ID basis. If you do not send the Epic-Client-ID HTTP header with the appropriate production or non-production client ID associated with your application in your call to the metadata endpoint, you can receive the wrong token and authorize endpoints. Additional CORS setup might be necessary on the Epic community member's Interconnect server to allow for this header.

Starting in the November 2021 version of Epic, by including an Epic Client ID, clients authorized to perform dynamic client registration can then determine which endpoint to use when performing dynamic client registration. Note that this capability is supported for only STU3 and R4 requests.

Here's an example of what a full metadata request might look like with the additional Epic-Client-ID header.

GET https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/metadata HTTP/1.1
Accept: application/fhir+json
Epic-Client-ID: 0000-0000-0000-0000-0000
Step 3: Your Application Requests an Authorization Code
Your application now has a launch token obtained from the initial EHR launch as well as the authorize endpoint obtained from the metadata query. To exchange the launch token for an authorization code, your app needs to either make an HTTP GET or POST request to the authorize endpoint that contains the parameters below. POST requests are supported for EHR launches in Epic version November 2020 and later, and are not currently supported for standalone launches.

For POST requests, the parameters should be in the body of the request and should be sent as Content-Type "application/x-www-form-urlencoded". For GET requests, the parameters should be appended in the querystring of the request. It is Epic's recommendation to use HTTP POST for EHR launches to overcome any size limits on the request URL.

In either case, the application must redirect the User-Agent (the user's browser) to the authorization server by either submitting an HTML Form to the authorization server (for HTTP POST) or by redirecting to a specified URL (for HTTP GET). The request should contain the following parameters.

response_type: This parameter must contain the value "code".
client_id: This parameter contains your web application's client ID issued by Epic.
redirect_uri: This parameter contains your application's redirect URI. After the request completes on the Epic server, this URI will be called as a callback. The value of this parameter needs to be URL encoded. This URI must also be registered with the EHR's authorization server by adding it to your app listing.
scope: This parameter describes the information for which the web application is requesting access. Starting with the Epic 2018 version, a scope of "launch" is required for EHR launch workflows. Starting with the November 2019 version of Epic, OpenID Connect scopes are supported, specifically the "openid" scope is supported for all apps and the "fhirUser" scope is supported by apps with the R4 (or greater) SMART on FHIR version selected.
launch: This parameter is required for EHR launch workflows. The value to use will be passed from the EHR.
aud: Starting in the August 2021 version of Epic, health care organizations can optionally configure their system to require the aud parameter for EHR launch workflows if a launch context is included in the scope parameter. Starting in the May 2023 version of Epic, this parameter will be required. The value to use is the FHIR base URL of the resource server the application intends to access, which is typically the FHIR server returned by the iss.
state: This optional parameter is generated by your app and is opaque to the EHR. The EHR's authorization server will append it to each subsequent exchange in the workflow for you to validate session integrity. While not required, this parameter is recommended to be included and validated with each exchange in order to increase security. For more information see RFC 6819 Section 3.6.
Note: Large state values in combination with launch tokens that are JWTs (see above) may cause the query string for the HTTP GET request to the authorization endpoint to exceed the Epic community member web server's max query string length and cause the request to fail. You can mitigate this risk by:
Following the SMART App Launch Framework's recommendation that the state parameter be an unpredictable value ... with at least 122 bits of entropy (e.g., a properly configured random uuid is suitable), and not store any actual application state in the state parameter.
Using a POST request. If you use this approach, note that you might still need to account for a large state value in the HTTP GET redirect back to your own server.
Additional parameters for native mobile apps (available starting in the August 2019 version of Epic):

code_challenge: This optional parameter is generated by your app and used for PKCE. This is the S256 hashed version of the code_verifier parameter, which will be used in the token request.
code_challenge_method: This optional parameter indicates the method used for the code_challenge parameter and is required if using that parameter. Currently, only the S256 method is supported.
Here's an example of an authorization request using HTTP GET. You will replace the [redirect_uri], [client_id], [launch_token], [state], [code_challenge], and [audience] placeholders with your own values.

https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize?scope=launch&response_type=code&redirect_uri=[redirect_uri]&client_id=[client_id]&launch=[launch_token]&state=[state]&code_challenge=[code_challenge]&code_challenge_method=S256&aud=[audience]
This is an example HTTP GET from the SMART on FHIR launchpad:

https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize?scope=launch&response_type=code&redirect_uri=https%3A%2F%2Ffhir.epic.com%2Ftest%2Fsmart&client_id=d45049c3-3441-40ef-ab4d-b9cd86a17225&launch=GwWCqm4CCTxJaqJiROISsEsOqN7xrdixqTl2uWZhYxMAS7QbFEbtKgi7AN96fKc2kDYfaFrLi8LQivMkD0BY-942hYgGO0_6DfewP2iwH_pe6tR_-fRfiJ2WB_-1uwG0&state=abc123&aud=https%3A%2F%2Ffhir.epic.com%2Finterconnect-fhir-oauth%2Fapi%2Ffhir%2Fdstu2
And here's an example of what the same request would look like as an HTTP Post:


POST https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize HTTP/1.1
Content-Type: application/x-www-form-urlencoded

scope=launch&response_type=code&redirect_uri=https%3A%2F%2Ffhir.epic.com%2Ftest%2Fsmart&client_id=d45049c3-3441-40ef-ab4d-b9cd86a17225&launch=GwWCqm4CCTxJaqJiROISsEsOqN7xrdixqTl2uWZhYxMAS7QbFEbtKgi7AN96fKc2kDYfaFrLi8LQivMkD0BY-942hYgGO0_6DfewP2iwH_pe6tR_-fRfiJ2WB_-1uwG0&state=abc123&aud=https%3A%2F%2Ffhir.epic.com%2Finterconnect-fhir-oauth%2Fapi%2Ffhir%2Fdstu2 
Step 4: EHR's Authorization Server Reviews the Request
The EHR's authorization server reviews the request from your application. If approved, the authorization server redirects the browser to the redirect URL supplied in the initial request and appends the following querystring parameter.

code: This parameter contains the authorization code generated by Epic, which will be exchanged for the access token in the next step.
See the Epic-Issued OAuth 2.0 Tokens appendix section for details on handling authorization codes.
state: This parameter will have the same value as the earlier state parameter. For more information, refer to Step 3.
Here's an example of what the redirect will look like if Epic's authorization server accepts the request:

https://fhir.epic.com/test/smart?code=yfNg-rSc1t5O2p6jVAZLyY00uOOte5KM1y3YUxqsJQnBKEMNsYqOPTyVqcCH3YXaPkLztO9Rvf7bhLqQTwALHcHN6raxpTbR1eVgV2QyLA_4K0HrJO92et3qRXiXPkj7&state=abc123
Step 5: Your Application Exchanges the Authorization Code for an Access Token
After receiving the authorization code, your application trades the code for a JSON object containing an access token and contextual information by sending an HTTP POST to the token endpoint using a Content-Type header with value of "application/x-www-form-urlencoded". For more information, see RFC 6749 section 4.1.3.

Access Token Request: Non-confidential Clients
The following parameters are required in the POST body:

grant_type: For the EHR launch flow, this should contain the value "authorization_code".
code: This parameter contains the authorization code sent from Epic's authorization server to your application as a querystring parameter on the redirect URI as described above.
redirect_uri: This parameter must contain the same redirect URI that you provided in the initial access request. The value of this parameter needs to be URL encoded.
client_id: This parameter must contain the application's client ID issued by Epic that you provided in the initial request.
code_verifier: This optional parameter is used to verify against your code_challenge parameter when using PKCE. This parameter is passed as free text and must match the code_challenge parameter used in your authorization request once it is hashed on the server using the code_challenge_method. This parameter is available starting in the August 2019 version of Epic.
Here's an example of what an HTTP POST request for an access token might look like:

POST https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token HTTP/1.1
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&code=yfNg-rSc1t5O2p6jVAZLyY00uOOte5KM1y3YUxqsJQnBKEMNsYqOPTyVqcCH3YXaPkLztO9Rvf7bhLqQTwALHcHN6raxpTbR1eVgV2QyLA_4K0HrJO92et3qRXiXPkj7&redirect_uri=https%3A%2F%2Ffhir.epic.com%2Ftest%2Fsmart&client_id=d45049c3-3441-40ef-ab4d-b9cd86a17225 
The authorization server responds to the HTTP POST request with a JSON object that includes an access token. The response contains the following fields:

access_token: This parameter contains the access token issued by Epic to your application and is used in future requests.
See the Epic-Issued OAuth 2.0 Tokens appendix section for details on handling access tokens.
token_type: In Epic's OAuth 2.0 implementation, this parameter always includes the value bearer.
expires_in: This parameter contains the number of seconds for which the access token is valid.
scope: This parameter describes the access your application is authorized for.
id_token: Returned only for applications that have requested an openid scope. See below for more info on OpenID Connect id_tokens. This parameter follows the guidelines of the OpenID Connect (OIDC) Core 1.0 specification. It is signed but not encrypted.
patient: This parameter identifies provides the FHIR ID for the patient, if a patient is in context at time of launch.
epic.dstu2.patient: This parameter identifies the DSTU2 FHIR ID for the patient, if a patient is in context at time of launch.
encounter: This parameter identifies the FHIR ID for the patient's encounter, if in context at time of launch. The encounter token corresponds to the FHIR Encounter resource.
location : This parameter identifies the FHIR ID for the encounter department, if in context at time of launch. The location token corresponds to the FHIR Location resource.
appointment: This parameter identifies the FHIR ID for the patient's appointment, if appointment context is available at time of launch. The appointment token corresponds to the FHIR Appointment resource.
loginDepartment: This parameter identifies the FHIR ID of the user's login department for launches from Hyperspace. The loginDepartment token corresponds to the FHIR Location resource.
state: This parameter will have the same value as the earlier state parameter. For more information, refer to Step 3.
Note that you can include additional fields in the response if needed based on the integration configuration. For more information, refer to the Launching your app topic. Here's an example of what a JSON object including an access token might look like:

{
"access_token": "Nxfve4q3H9TKs5F5vf6kRYAZqzK7j9LHvrg1Bw7fU_07_FdV9aRzLCI1GxOn20LuO2Ahl5RkRnz-p8u1MeYWqA85T8s4Ce3LcgQqIwsTkI7wezBsMduPw_xkVtLzLU2O",
"token_type": "bearer",
"expires_in": 3240,
"scope": "openid Patient.read Patient.search ",
"id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IktleUlEIiwidHlwIjoiSldUIn0.eyJhdWQiOiJDbGllbnRJRCIsImV4cCI6RXhwaXJlc0F0LCJpYXQiOklzc3VlZEF0LCJpc3MiOiJJc3N1ZXJVUkwiLCJzdWIiOiJFbmRVc2VySWRlbnRpZmllciJ9",
"__epic.dstu2.patient": "T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB",
"patient": "T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB",
"appointment": "eVa-Ad1SCIenVq8CYQVxfKwGtP-DfG3nIy9-5oPwTg2g3",
"encounter": "eySnzekbpf6uGZz87ndPuRQ3",
"location": "e4W4rmGe9QzuGm2Dy4NBqVc0KDe6yGld6HW95UuN-Qd03",
"loginDepartment": "e4W4rmGe9QzuGm2Dy4NBqVc0KDe6yGld6HW95UuN-Qd03",
"state": "abc123",
}
At this point, authorization is complete and the web application can access the protected patient data it requests using FHIR APIs.

Access Token Request: Frontend Confidential Clients
Consult Standalone Launch: Access Token Request for Frontend Confidential Clients for details on how to obtain an access token if your app is a confidential client.

OpenID Connect id_tokens
Epic started supporting the OpenID Connect id_token in the access token response for apps that request the openid scope since the November 2019 version of Epic.

A decoded OpenID Connect id_token JWT will have these headers:

Header	Description
alg	The JWT authentication algorithm. Currently only RSA 256 is supported in id_token JWTs so this will always be RS256.
typ	This is always set to JWT.
kid	The base64 encoded SHA-256 hash of the public key.
A decoded OpenID Connect id_token JWT will have this payload:

Claim	Description	Remarks
iss	Issuer of the JWT. This is set to the token endpoint that should be used by the client.	Starting in the May 2020 version of Epic, the iss will be set to the OAuth 2.0 server endpoint, e.g. https://<Interconnect Server URL>/oauth2. For Epic versions prior to May 2020, it is set to the OAuth 2.0 token endpoint, e.g. https://<Interconnect Server URL>/oauth2/token.
sub	STU3+ FHIR ID for the resource representing the user launching the app.	For Epic integrations, the sub and fhirUser claims reference one of the following resources depending on the type of workflow:
Provider/user workflows: Practitioner resource
MyChart self access workflows: Patient resource
MyChart proxy access workflows: RelatedPerson resource
Note apps with a SMART on FHIR version of DSTU2 will still get a STU3+ FHIR FHIR ID for the user. The STU3+ Practitioner.Read or RelatedPerson.Read APIs would be required to read the Practitioner or RelatedPerson FHIR IDs. Patient FHIR IDs can be used across FHIR versions in Epic's implementation.
fhirUser	Absolute reference to the FHIR resource representing the user launching the app. See the HL7 documentation for more details.	The fhirUser claim will only be present if app has the R4 (or greater) SMART on FHIR version selected, and requests both the openid and fhirUser scopes in the request to the authorize endpoint. See the remark for the sub claim above for more information about what the resource returned in these claims represents.
aud	Audiences that the ID token is intended for. This will be set to the client ID for the application that was just authorized during the SMART on FHIR launch.	
iat	Time integer for when the JWT was created, expressed in seconds since the "Epoch" (1970-01-01T00:00:00Z UTC).	
exp	Expiration time integer for this authentication JWT, expressed in seconds since the "Epoch" (1970-01-01T00:00:00Z UTC).	This is set to the current time plus 5 minutes.
preferred_username	The user's LDAP/AD down-level logon name.	This claim is supported in Epic version February 2021 and later. The preferred_username claim will be present only if the app requests both the openid and profile scopes in the request to the authorize endpoint.
nonce	The nonce for this client session.	The nonce claim will be present only if it was specified in the authorization request. This is an identifier for the client session. For more information about the nonce, refer to the Authentication Request section of the OpenID specification.
Here is an example decoded id_token that could be returned if the app has the R4 (or greater) SMART on FHIR version selected, and requests both the openid and fhirUser scopes in the request to the authorize endpoint:

{
"alg": "RS256",
"kid": "liCulTIaitUzjfUh2AqNiMro47X9HcVcd9XPi8LDJKA=",
"typ": "JWT"
}
{
"aud": "de5dae1a-4317-4c25-86f1-ed558e85529b",
"exp": 1595956317,
"fhirUser": "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/api/FHIR/R4/Practitioner/exfo6E4EXjWsnhA1OGVElgw3",
"iat": 1595956017,
"iss": "https://fhir.epic.com/interconnect-fhir-oauth/oauth2",
"sub": "exfo6E4EXjWsnhA1OGVElgw3"
}
Here is an example decoded id_token that could be returned if the app requests at least the openid scope in the request to the authorize endpoint, but either doesn't request the fhirUser claim or doesn't meet the criteria outlined above for receiving the fhirUser claim:

{
"alg": "RS256",
"kid": "liCulTIaitUzjfUh2AqNiMro47X9HcVcd9XPi8LDJKA=",
"typ": "JWT"
}
{
"aud": "de5dae1a-4317-4c25-86f1-ed558e85529b",
"exp": 1595956317,
"iat": 1595956017,
"iss": "https://fhir.epic.com/interconnect-fhir-oauth/oauth2",
"sub": "exfo6E4EXjWsnhA1OGVElgw3"
}
Validating the OpenID Connect JSON Web Token
When completing the OAuth 2.0 authorization workflow with the openid scope, the JSON Web Token (JWT) returned in the id_token field will be cryptographically signed. The public key to verify the authenticity of the JWT can be found at https://<Interconnect Server URL>/api/epic/2019/Security/Open/PublicKeys/530005/OIDC, for example https://fhir.epic.com/interconnect-fhir-oauth/api/epic/2019/Security/Open/PublicKeys/530005/OIDC.

Starting in the May 2020 version of Epic, metadata about the server's OpenID Connect configuration, including the jwks_uri OIDC public key endpoint, can be found at the OpenID configuration endpoint https://<Interconnect Server URL>/oauth2/.well-known/openid-configuration, for example https://fhir.epic.com/interconnect-fhir-oauth/oauth2/.well-known/openid-configuration.

Starting in the August 2021 version of Epic, metadata about the server's OpenID Connect configuration can also be found at the FHIR endpoint https://<Interconnect Server URL>/api/FHIR/R4/.well-known/openid-configuration, for example https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4/.well-known/openid-configuration.

Step 6: Your Application Uses FHIR APIs to Access Patient Data
With a valid access token, your application can now access protected patient data from the EHR database using FHIR APIs. Queries must contain an Authorization header that includes the access token presented as a Bearer token.

Here's an example of what a valid query looks like:

GET https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/DSTU2/Patient/T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB HTTP/1.1
Authorization: Bearer Nxfve4q3H9TKs5F5vf6kRYAZqzK7j9LHvrg1Bw7fU_07_FdV9aRzLCI1GxOn20LuO2Ahl5RkRnz-p8u1MeYWqA85T8s4Ce3LcgQqIwsTkI7wezBsMduPw_xkVtLzLU2O
Step 7: Use a Refresh Token to Obtain a New Access Token
Refresh tokens are not typically needed for embedded (SMART on FHIR) launches because users are not required to log in to Epic during the SMART on FHIR launch process, and the access token obtained from the launch process is typically valid for longer than the user needs to use the app.

Consult the Standalone Launch: Use a Refresh Token to Obtain a New Access Token for details on how to use a refresh token to get a new an access token if your app uses refresh tokens.

Standalone Launch
Contents

How It Works
Step 1: Your Application Requests an Authorization Code
Step 2: EHR's Authorization Server Authenticates the User and Authorizes Access
Step 3: Your Application Exchanges the Authorization Code for an Access Token
Non-confidential Clients
Frontend Confidential Clients
Step 4: Your Application Uses FHIR APIs to Access Patient Data
Step 5: Use a Refresh Token to Obtain a New Access Token
Offline Access for Native and Browser-Based Applications
Step 1: Get the initial access token you'll use to register a dynamic client
Step 2: Register the dynamic client
Step 3: Get an access token you can use to retrieve FHIR resources
Step 3a: Get an access token using the JWT bearer flow
Step 3b: Alternate flow with refresh tokens
How It Works
The app launches directly to the authorize endpoint outside of an EHR session and requests context from the EHR's authorization server.


Step 1: Your Application Requests an Authorization Code
Your application would like to authenticate the user using the OAuth 2.0 workflow. To initiate this process, your app needs to link (using HTTP GET) to the authorize endpoint and append the following querystring parameters:

response_type: This parameter must contain the value "code".
client_id: This parameter contains your web application's client ID issued by Epic.
redirect_uri: This parameter contains your application's redirect URI. After the request completes on the Epic server, this URI will be called as a callback. The value of this parameter needs to be URL encoded. This URI must also be registered with the EHR's authorization server by adding it to your app listing.
state: This optional parameter is generated by your app and is opaque to the EHR. The EHR's authorization server will append it to each subsequent exchange in the workflow for you to validate session integrity. While not required, this parameter is recommended to be included and validated with each exchange in order to increase security. For more information see RFC 6819 Section 3.6.
scope: This parameter describes the information for which the web application is requesting access. Starting with the November 2019 version of Epic, the "openid" and "fhirUser" OpenID Connect scopes are supported. While scope is optional in Epic's SMART on FHIR implementation, it's required for testing in the sandbox. Providing scope=openid is sufficient.
aud: Starting in the August 2021 version of Epic, health care organizations can optionally configure their system to require the aud parameter for Standalone and EHR launch workflows if a launch context is included in the scope parameter. Starting in the May 2023 version of Epic, this parameter will be required. The value to use is the base URL of the resource server the application intends to access, which is typically the FHIR server.
Additional parameters for native mobile apps (available starting in the August 2019 version of Epic):

code_challenge: This optional parameter is generated by your app and used for PKCE. This is the S256 hashed version of the code_verifier parameter, which will be used in the token request.
code_challenge_method: This optional parameter indicates the method used for the code_challenge parameter and is required if using that parameter. Currently, only the S256 method is supported.
Here's an example of an authorization request using HTTP GET. You will replace the [redirect_uri], [client_id], [state], and [audience] placeholders with your own values.

https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize?response_type=code&redirect_uri=[redirect_uri]&client_id=[client_id]&state=[state]&aud=[audience]&scope=[scope]
This is an example link:

https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize?response_type=code&redirect_uri=https%3A%2F%2Ffhir.epic.com%2Ftest%2Fsmart&client_id=d45049c3-3441-40ef-ab4d-b9cd86a17225&state=abc123&aud=https%3A%2F%2Ffhir.epic.com%2Finterconnect-fhir-oauth%2Fapi%2Ffhir%2Fdstu2&scope=openid
Step 2: EHR's Authorization Server Authenticates the User and Authorizes Access
The EHR's authorization server reviews the request from your application, authenticates the user (sample credentials found here), and authorizes access. If approved, the authorization server redirects the browser to the redirect URL supplied in the initial request and appends the following querystring parameter.

code: This parameter contains the authorization code generated by Epic, which will be exchanged for the access token in the next step.
See the Epic-Issued OAuth 2.0 Tokens appendix section for details on handling authorization codes.
state: This parameter will have the same value as the earlier state parameter. For more information, refer to Step 1.
Here's an example of what the redirect will look like if Epic's authorization server accepts the request:

https://fhir.epic.com/test/smart?code=yfNg-rSc1t5O2p6jVAZLyY00uOOte5KM1y3YUxqsJQnBKEMNsYqOPTyVqcCH3YXaPkLztO9Rvf7bhLqQTwALHcHN6raxpTbR1eVgV2QyLA_4K0HrJO92et3qRXiXPkj7&state=abc123
Step 3: Your Application Exchanges the Authorization Code for an Access Token
After receiving the authorization code, your application trades the code for a JSON object containing an access token and contextual information by sending an HTTP POST to the token endpoint using a Content-Type header with value of "application/x-www-form-urlencoded". For more information, see RFC 6749 section 4.1.3.

Access Token Request: Non-confidential Clients
The following parameters are required in the POST body:

grant_type: For the Standalone launch flow, this should contain the value "authorization_code".
code: This parameter contains the authorization code sent from Epic's authorization server to your application as a querystring parameter on the redirect URI as described above.
redirect_uri: This parameter must contain the same redirect URI that you provided in the initial access request. The value of this parameter needs to be URL encoded.
client_id: This parameter must contain the application's client ID issued by Epic that you provided in the initial request.
code_verifier: This optional parameter is used to verify against your code_challenge parameter when using PKCE. This parameter is passed as free text and must match the code_challenge parameter used in your authorization request once it is hashed on the server using the code_challenge_method. This parameter is available starting in the August 2019 version of Epic.
Here's an example of what an HTTP POST request for an access token might look like:

POST https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token HTTP/1.1
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&code=yfNg-rSc1t5O2p6jVAZLyY00uOOte5KM1y3YUxqsJQnBKEMNsYqOPTyVqcCH3YXaPkLztO9Rvf7bhLqQTwALHcHN6raxpTbR1eVgV2QyLA_4K0HrJO92et3qRXiXPkj7&redirect_uri=https%3A%2F%2Ffhir.epic.com%2Ftest%2Fsmart&client_id=d45049c3-3441-40ef-ab4d-b9cd86a17225 
The authorization server responds to the HTTP POST request with a JSON object that includes an access token. The response contains the following fields:

access_token: This parameter contains the access token issued by Epic to your application and is used in future requests.
See the Epic-Issued OAuth 2.0 Tokens appendix section for details on handling access tokens.
token_type: In Epic's OAuth 2.0 implementation, this parameter always includes the value bearer.
expires_in: This parameter contains the number of seconds for which the access token is valid.
scope: This parameter describes the access your application is authorized for.
id_token: Returned only for applications that have requested an openid scope. See above for more info on OpenID Connect id_tokens. This parameter follows the guidelines described earlier in this document.
patient: For patient-facing workflows, this parameter identifies the FHIR ID for the patient on whose behalf authorization to the system was granted.
The patient's FHIR ID is not returned for provider-facing standalone launch workflows.
epic.dstu2.patient: For patient-facing workflows, this parameter identifies the DSTU2 FHIR ID for the patient on whose behalf authorization to the system was granted.
The patient's FHIR ID is not returned for provider-facing standalone launch workflows.
Note that you can pass additional parameters if needed based on the integration configuration. Here's an example of what a JSON object including an access token might look like:

{
"access_token": "Nxfve4q3H9TKs5F5vf6kRYAZqzK7j9LHvrg1Bw7fU_07_FdV9aRzLCI1GxOn20LuO2Ahl5RkRnz-p8u1MeYWqA85T8s4Ce3LcgQqIwsTkI7wezBsMduPw_xkVtLzLU2O",
"token_type": "bearer",
"expires_in": 3240,
"scope": "Patient.read Patient.search ",
"patient": "T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB"
}
At this point, authorization is complete and the web application can access the protected patient data it requested using FHIR APIs.

Access Token Request: Frontend Confidential Clients
There are two authentication options available for confidential apps that can keep authentication credentials secret:

Client Secret Authentication
JSON Web Token (JWT) Authentication
Access Token Request: Frontend Confidential Clients with Client Secret Authentication
After receiving the authorization code, your application trades the code for a JSON object containing an access token and contextual information by sending an HTTP POST to the token endpoint using a Content-Type header with value of "application/x-www-form-urlencoded". For more information, see RFC 6749 section 4.1.3.

The Epic on FHIR website can generate a client secret (effectively a password) for your app to use to obtain refresh tokens, and store the hashed secret for you, or Epic community members can upload a client secret hash that you provide them when they activate your app for their system. If you provide community members a client secret hash to upload, you should use a unique client secret per Epic community member and per environment type (non-production and production) for each Epic community member.

The following parameters are required in the POST body:

grant_type: This should contain the value authorization_code.
code: This parameter contains the authorization code sent from Epic's authorization server to your application as a querystring parameter on the redirect URI as described above.
redirect_uri: This parameter must contain the same redirect URI that you provided in the initial access request. The value of this parameter needs to be URL encoded.
Note: The client_id parameter is not passed in the the POST body if you use client secret authentication, which is different from the access token request for apps that do not use refresh tokens. You will instead pass an Authorization HTTP header with client_id and client_secret URL encoded and passed as a username and password. Conceptually the Authorization HTTP header will have this value: base64(client_id:client_secret).

For example, using the following client_id and client_secret:

client_id: d45049c3-3441-40ef-ab4d-b9cd86a17225

URL encoded client_id: d45049c3-3441-40ef-ab4d-b9cd86a17225 Note: base64 encoding Epic's client IDs will have no effect

client_secret: this-is-the-secret-2/7

URL encoded client_secret: this-is-the-secret-2%2F7

Would result in this Authorization header:

Authorization: Basic base64Encode{d45049c3-3441-40ef-ab4d-b9cd86a17225:this-is-the-secret-2%2F7}
or

Authorization: Basic ZDQ1MDQ5YzMtMzQ0MS00MGVmLWFiNGQtYjljZDg2YTE3MjI1OnRoaXMtaXMtdGhlLXNlY3JldC0yJTJGNw==
Here's an example of what a valid HTTP POST might look like:

POST https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token HTTP/1.1
Content-Type: application/x-www-form-urlencoded 
Authorization: Basic ZDQ1MDQ5YzMtMzQ0MS00MGVmLWFiNGQtYjljZDg2YTE3MjI1OnRoaXMtaXMtdGhlLXNlY3JldC0yJTJGNw==

grant_type=authorization_code&code=yfNg-rSc1t5O2p6jVAZLyY00uOOte5KM1y3YUxqsJQnBKEMNsYqOPTyVqcCH3YXaPkLztO9Rvf7bhLqQTwALHcHN6raxpTbR1eVgV2QyLA_4K0HrJO92et3qRXiXPkj7&redirect_uri=https%3A%2F%2Ffhir.epic.com%2Ftest%2Fsmart
The authorization server responds to the HTTP POST request with a JSON object that includes an access token and a refresh token. The response contains the following fields:

refresh_token: This parameter contains the refresh token issued by Epic to your application and can be used to obtain a new access token. For more information on how this works, see Step 5.
See the Epic-Issued OAuth 2.0 Tokens appendix section for details on handling refresh tokens.
access_token: This parameter contains the access token issued by Epic to your application and is used in future requests.
See the Epic-Issued OAuth 2.0 Tokens appendix section for details on handling access tokens.
token_type: In Epic's OAuth 2.0 implementation, this parameter always includes the value bearer.
expires_in: This parameter contains the number of seconds for which the access token is valid.
scope: This parameter describes the access your application is authorized for.
id_token: Returned only for applications that have requested an openid scope. See above for more info on OpenID Connect id_tokens. This parameter follows the guidelines of the OpenID Connect (OIDC) Core 1.0 specification. It is signed but not encrypted.
patient: For patient-facing workflows, this parameter identifies the FHIR ID for the patient on whose behalf authorization to the system was granted.
The patient's FHIR ID is not returned for provider-facing standalone launch workflows.
epic.dstu2.patient: For patient-facing workflows, this parameter identifies the DSTU2 FHIR ID for the patient on whose behalf authorization to the system was granted.
The patient's FHIR ID is not returned for provider-facing standalone launch workflows.
encounter: This parameter identifies the FHIR ID for the patient's encounter, if in context at time of launch. The encounter token corresponds to the FHIR Encounter resource.
The encounter FHIR ID is not returned for standalone launch workflows.
location: This parameter identifies the FHIR ID for the ecounter department, if in context at time of launch. The location token corresponds to the FHIR Location resource.
The location FHIR ID is not returned for standalone launch workflows.
appointment: This parameter identifies the FHIR ID for the patient's appointment, if appointment context is available at time of launch. The appointment token corresponds to the FHIR Appointment resource.
The appointment FHIR ID is not returned for standalone launch workflows.
loginDepartment: This parameter identifies the FHIR ID of the user's login department for launches from Hyperspace. The loginDepartment token corresponds to the FHIR Location resource.
The loginDepartment FHIR ID is not returned for standalone launch workflows.
Note that you can pass additional parameters if needed based on the integration configuration. Here's an example of what a JSON object including an access token and refres token might look like:

{
"access_token": "Nxfve4q3H9TKs5F5vf6kRYAZqzK7j9LHvrg1Bw7fU_07_FdV9aRzLCI1GxOn20LuO2Ahl5RkRnz-p8u1MeYWqA85T8s4Ce3LcgQqIwsTkI7wezBsMduPw_xkVtLzLU2O",
"refresh_token": "H9TKs5F5vf6kRYAZqzK7j9L_07_FdV9aRzLCI1GxOn20LuO2Ahl5R1MeYWqA85T8s4sTkI7wezBsMduPw_xkLzLU2O",
"token_type": "bearer",
"expires_in": 3240,
"scope": "Patient.read Patient.search ",
"patient": "T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB"
}
At this point, authorization is complete and the web application can access the protected patient data it requested using FHIR APIs.

Access Token Request: Frontend Confidential Clients with JSON Web Token (JWT) Authentication
After receiving the authorization code, your application trades the code for a JSON object containing an access token and contextual information by sending an HTTP POST to the token endpoint using a Content-Type header with value of "application/x-www-form-urlencoded". For more information, see RFC 6749 section 4.1.3.

You can use a one-time use JSON Web Token (JWT) to authenticate your app to the authorization server and obtain an access token and/or refresh token. There are several libraries for creating JWTs. See jwt.io for some examples. You'll pre-register a JSON Web Key Set or JWK Set URL for a given Epic community member environment on the Epic on FHIR website and then use the corresponding private key to create a signed JWT. Frontend apps using JWT authentication must use a JSON Web Key Set or JWK Set URL as static public keys are not supported.

See the Creating a Public Private Key Pair for JWT Signature and the Creating a JWT sections for details on how to create a signed JWT.

The following parameters are required in the POST body:

grant_type: This should contain the value authorization_code.
code: This parameter contains the authorization code sent from Epic's authorization server to your application as a querystring parameter on the redirect URI as described above.
redirect_uri: This parameter must contain the same redirect URI that you provided in the initial access request. The value of this parameter needs to be URL encoded.
client_assertion_type: This should be set to urn:ietf:params:oauth:client-assertion-type:jwt-bearer.
client_assertion: This will be the one-time use JSON Web Token (JWT) your app generated using the steps mentioned above.
Here's an example of what a valid HTTP POST might look like:

POST https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token HTTP/1.1
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&client_assertion_type=urn%3Aietf%3Aparams%3Aoauth%3Aclient-assertion-type%3Ajwt-bearer&code=yfNg-rSc1t5O2p6jVAZLyY00uOOte5KM1y3YUxqsJQnBKEMNsYqOPTyVqcCH3YXaPkLztO9Rvf7bhLqQTwALHcHN6raxpTbR1eVgV2QyLA_4K0HrJO92et3qRXiXPkj7&redirect_uri=https%3A%2F%2Ffhir.epic.com%2Ftest%2Fsmart&client_assertion=eyJhbGciOiJSUzM4NCIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJkNDUwNDljMy0zNDQxLTQwZWYtYWI0ZC1iOWNkODZhMTcyMjUiLCJzdWIiOiJkNDUwNDljMy0zNDQxLTQwZWYtYWI0ZC1iOWNkODZhMTcyMjUiLCJhdWQiOiJodHRwczovL2ZoaXIuZXBpYy5jb20vaW50ZXJjb25uZWN0LWZoaXItb2F1dGgvb2F1dGgyL3Rva2VuIiwianRpIjoiZjllYWFmYmEtMmU0OS0xMWVhLTg4ODAtNWNlMGM1YWVlNjc5IiwiZXhwIjoxNTgzNTI0NDAyLCJuYmYiOjE1ODM1MjQxMDIsImlhdCI6MTU4MzUyNDEwMn0.dztrzHo9RRwNRaB32QxYLaa9CcIMoOePRCbpqsRKgyJmBOGb9acnEZARaCzRDGQrXccAQ9-syuxz5QRMHda0S3VbqM2KX0VRh9GfqG3WJBizp11Lzvc2qiUPr9i9CqjtqiwAbkME40tioIJMC6DKvxxjuS-St5pZbSHR-kjn3ex2iwUJgPbCfv8cJmt19dHctixFR6OG-YB6lFXXpNP8XnL7g85yLOYoQcwofN0k8qK8h4uh8axTPC21fv21mCt50gx59XgKsszysZnMDt8OG_G4gjk_8JnGHwOVkJhqj5oeg_GdmBhQ4UPuxt3YvCOTW9S2vMikNUnxrhdVvn2GVg

The authorization server responds to the HTTP POST request with a JSON object that includes an access token and a refresh token. The response contains the following fields:

refresh_token: If your app is configured to receive refresh tokens, this parameter contains the refresh token issued by Epic to your application and can be used to obtain a new access token. For more information on how this works, see Step 5.
See the Epic-Issued OAuth 2.0 Tokens appendix section for details on handling refresh tokens.
access_token: This parameter contains the access token issued by Epic to your application and is used in future requests.
See the Epic-Issued OAuth 2.0 Tokens appendix section for details on handling access tokens.
token_type: In Epic's OAuth 2.0 implementation, this parameter always includes the value bearer.
expires_in: This parameter contains the number of seconds for which the access token is valid.
scope: This parameter describes the access your application is authorized for.
id_token: Returned only for applications that have requested an openid scope. See above for more info on OpenID Connect id_tokens. This parameter follows the guidelines of the OpenID Connect (OIDC) Core 1.0 specification. It is signed but not encrypted.
patient: For patient-facing workflows, this parameter identifies the FHIR ID for the patient on whose behalf authorization to the system was granted.
The patient's FHIR ID is not returned for provider-facing standalone launch workflows.
epic.dstu2.patient: For patient-facing workflows, this parameter identifies the DSTU2 FHIR ID for the patient on whose behalf authorization to the system was granted.
The patient's FHIR ID is not returned for provider-facing standalone launch workflows.
encounter: This parameter identifies the FHIR ID for the patient's encounter, if in context at time of launch. The encounter token corresponds to the FHIR Encounter resource.
The encounter FHIR ID is not returned for standalone launch workflows.
location: This parameter identifies the FHIR ID for the encounter department, if in context at time of launch. The location token corresponds to the FHIR Location resource.
The location FHIR ID is not returned for standalone launch workflows.
appointment: This parameter identifies the FHIR ID for the patient's appointment, if appointment context is available at time of launch. The appointment token corresponds to the FHIR Appointment resource.
The appointment FHIR ID is not returned for standalone launch workflows.
loginDepartment: This parameter identifies the FHIR ID of the user's login department for launches from Hyperspace. The loginDepartment token corresponds to the FHIR Location resource.
The loginDepartment FHIR ID is not returned for standalone launch workflows.
Note that you can pass additional parameters if needed based on the integration configuration. Here's an example of what a JSON object including an access token might look like:

{
  "access_token": "Nxfve4q3H9TKs5F5vf6kRYAZqzK7j9LHvrg1Bw7fU_07_FdV9aRzLCI1GxOn20LuO2Ahl5RkRnz-p8u1MeYWqA85T8s4Ce3LcgQqIwsTkI7wezBsMduPw_xkVtLzLU2O",
  "refresh_token": "H9TKs5F5vf6kRYAZqzK7j9L_07_FdV9aRzLCI1GxOn20LuO2Ahl5R1MeYWqA85T8s4sTkI7wezBsMduPw_xkLzLU2O",
  "token_type": "bearer",
  "expires_in": 3240,
  "scope": "Patient.read Patient.search ",
  "patient": "T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB"
}
At this point, authorization is complete and the web application can access the protected patient data it requested using FHIR APIs.

Step 4: Your Application Uses FHIR APIs to Access Patient Data
With a valid access token, your application can now access protected patient data from the EHR database using FHIR APIs. Queries must contain an Authorization header that includes the access token presented as a Bearer token.

Here's an example of what a valid query looks like:

GET https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/DSTU2/Patient/T1wI5bk8n1YVgvWk9D05BmRV0Pi3ECImNSK8DKyKltsMB HTTP/1.1
Authorization: Bearer Nxfve4q3H9TKs5F5vf6kRYAZqzK7j9LHvrg1Bw7fU_07_FdV9aRzLCI1GxOn20LuO2Ahl5RkRnz-p8u1MeYWqA85T8s4Ce3LcgQqIwsTkI7wezBsMduPw_xkVtLzLU2O
Step 5: Use a Refresh Token to Obtain a New Access Token
If your app uses refresh tokens (i.e. it can securely store credentials), then you can use a refresh token to request a new access token when the current access token expires (determined by the expires_in field from the authorization response from step 3).

There are two authentication options available for confidential apps that can keep authentication credentials secret:

Client Secret Authentication
JSON Web Token (JWT) Authentication
Using Refresh Tokens: If You Are Using Client Secret Authentication
Your application trades the refresh_token for a JSON object containing a new access token and contextual information by sending an HTTP POST to the token endpoint using a Content-Type HTTP header with value of "application/x-www-form-urlencoded". For more information, see RFC 6749 section 4.1.3.

The Epic on FHIR website can generate a client secret (effectively a password) for your app when using refresh tokens, and store the hashed secret for you, or Epic community members can upload a client secret hash that you provide them when they activate your app for their system. If you provide community members a client secret hash to upload, you should use a unique client secret per Epic community member and per environment type (non-production and production) for each Epic community member.

The following parameters are required in the POST body:

grant_type: This parameter always contains the value refresh_token.
refresh_token: The refresh token received from a prior authorization request.
An Authorization header using HTTP Basic Authentication is required, where the username is the URL encoded client_id and the password is the URL encoded client_secret.

For example, using the following client_id and client_secret:

client_id: d45049c3-3441-40ef-ab4d-b9cd86a17225

URL encoded client_id: d45049c3-3441-40ef-ab4d-b9cd86a17225 Note: base64 encoding Epic's client IDs will have no effect

client_secret: this-is-the-secret-2/7

URL encoded client_secret: this-is-the-secret-2%2F7

Would result in this Authorization header:

Authorization: Basic base64Encode{d45049c3-3441-40ef-ab4d-b9cd86a17225:this-is-the-secret-2%2F7}
or

Authorization: Basic ZDQ1MDQ5YzMtMzQ0MS00MGVmLWFiNGQtYjljZDg2YTE3MjI1OnRoaXMtaXMtdGhlLXNlY3JldC0yJTJGNw==
Here's an example of what a valid HTTP POST might look like:

POST https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token HTTP/1.1
Authorization: Basic ZDQ1MDQ5YzMtMzQ0MS00MGVmLWFiNGQtYjljZDg2YTE3MjI1OnRoaXMtaXMtdGhlLXNlY3JldC0yJTJGNw==
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token&refresh_token=j12xcniournlsdf234bgsd
The authorization server responds to the HTTP POST request with a JSON object that includes the new access token. The response contains the following fields:

access_token: This parameter contains the new access token issued.
token_type: In Epic's OAuth 2.0 implementation, this parameter always includes the value bearer.
expires_in: This parameter contains the number of seconds for which the access token is valid.
scope: This parameter describes the access your application is authorized for.
An example response to the previous request may look like the following:

{
"access_token": "57CjhZEdiTcCh1nqIwQUw5rODOLP3bSTnMEGNYbBerSeNn8hIUm6Mlc5ruCTfQawjRAoR8sYr8S_7vNdnJfgRKfD6s8mOqPnvJ8vZOHjEvy7l3Ra9frDaEAUBbN-j86k",
"token_type": "bearer",
"expires_in": 3240,
"scope": "Patient.read Patient.search"
}
Using Refresh Tokens: If You Are Using JSON Web Token Authentication
Your application trades the refresh_token for a JSON object containing a new access token and contextual information by sending an HTTP POST to the token endpoint using a Content-Type HTTP header with value of "application/x-www-form-urlencoded". For more information, see RFC 6749 section 4.1.3.

You can use a one-time use JSON Web Token (JWT) to authenticate your app to the authorization server to exchange the refresh token for a new access token. There are several libraries for creating JWTs. See jwt.io for some examples. You'll pre-register a JSON Web Key Set or JWK Set URL for a given Epic community member environment on the Epic on FHIR website and then use the corresponding private key to create a signed JWT. Frontend apps using JWT authentication must use a JSON Web Key Set or JWK Set URL as static public keys are not supported.

See the Creating a Public Private Key Pair for JWT Signature and the Creating a JWT sections for details on how to create a signed JWT.

The following parameters are required in the POST body:

grant_type: This should contain the value refresh_token.
refresh_token: The refresh token received from a prior authorization request.
client_assertion_type: This should be set to urn:ietf:params:oauth:client-assertion-type:jwt-bearer.
client_assertion: This will be the one-time use JSON Web Token (JWT) your app generated using the steps mentioned above.
Here's an example of what a valid HTTP POST might look like:

POST https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token HTTP/1.1
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token&client_assertion_type=urn%3Aietf%3Aparams%3Aoauth%3Aclient-assertion-type%3Ajwt-bearer&client_assertion=eyJhbGciOiJSUzM4NCIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJkNDUwNDljMy0zNDQxLTQwZWYtYWI0ZC1iOWNkODZhMTcyMjUiLCJzdWIiOiJkNDUwNDljMy0zNDQxLTQwZWYtYWI0ZC1iOWNkODZhMTcyMjUiLCJhdWQiOiJodHRwczovL2ZoaXIuZXBpYy5jb20vaW50ZXJjb25uZWN0LWZoaXItb2F1dGgvb2F1dGgyL3Rva2VuIiwianRpIjoiZjllYWFmYmEtMmU0OS0xMWVhLTg4ODAtNWNlMGM1YWVlNjc5IiwiZXhwIjoxNTgzNTI0NDAyLCJuYmYiOjE1ODM1MjQxMDIsImlhdCI6MTU4MzUyNDEwMn0.dztrzHo9RRwNRaB32QxYLaa9CcIMoOePRCbpqsRKgyJmBOGb9acnEZARaCzRDGQrXccAQ9-syuxz5QRMHda0S3VbqM2KX0VRh9GfqG3WJBizp11Lzvc2qiUPr9i9CqjtqiwAbkME40tioIJMC6DKvxxjuS-St5pZbSHR-kjn3ex2iwUJgPbCfv8cJmt19dHctixFR6OG-YB6lFXXpNP8XnL7g85yLOYoQcwofN0k8qK8h4uh8axTPC21fv21mCt50gx59XgKsszysZnMDt8OG_G4gjk_8JnGHwOVkJhqj5oeg_GdmBhQ4UPuxt3YvCOTW9S2vMikNUnxrhdVvn2GVg

The authorization server responds to the HTTP POST request with a JSON object that includes the new access token. The response contains the following fields:

access_token: This parameter contains the new access token issued.
token_type: In Epic's OAuth 2.0 implementation, this parameter always includes the value bearer.
expires_in: This parameter contains the number of seconds for which the access token is valid.
scope: This parameter describes the access your application is authorized for.
An example response to the previous request may look like the following:

{
  "access_token": "57CjhZEdiTcCh1nqIwQUw5rODOLP3bSTnMEGNYbBerSeNn8hIUm6Mlc5ruCTfQawjRAoR8sYr8S_7vNdnJfgRKfD6s8mOqPnvJ8vZOHjEvy7l3Ra9frDaEAUBbN-j86k",
  "token_type": "bearer",
  "expires_in": 3240,
  "scope": "Patient.read Patient.search"
}
Offline Access for Native and Browser-Based Applications
For a native client app (for example, an iOS mobile app or a Windows desktop app) or a browser-based app (for example, a single-page application) to use the confidential app profile in the SMART App Launch framework, that app needs to use "additional technology (such as dynamic client registration and universal redirect_uris) to protect the secret." If you have a native client or browser-based app, you can register a dynamic client to integrate with Epic using the steps below.

Step 1: Get the initial access token you'll use to register a dynamic client
Your app uses a flow like the one described above for a Standalone Launch. Note your application will specifically not be using a client secret, and will use its initial client ID issued by Epic.

The end-result of this flow is your app obtaining an initial access token (defined in RFC 7591) used for registering a client instance (step 2). This token is intentionally one-time-use and should be used for registration immediately.

Step 2: Register the dynamic client
To register the dynamic client, your application needs to:

Generate a public-private key pair on the user’s phone or computer.
Native apps can use the same strategies as backend apps to generate key sets
Browser-based apps can use the WebCrypto API
Securely store that device-specific key pair on the user’s device.
Browser-based apps using WebCrypto should follow key storage recommendations
Use the access token from step 1 to register a dynamic client using the OAuth 2.0 Dynamic Client Registration Protocol.
The client ID and private key should be associated with the Epic environment they are communicating with. Identify the Epic environment with its OAuth 2.0 server URL. If this is a backend integration or a subspace integration, the environment health system identifier (HSI) can be used to identify the environment instead.

This request must have two elements:

software_id: This parameter must contain the application’s client ID issued by Epic.
jwks: This parameter contains a JSON Web Key Set containing the public key from the key pair your application generated in step 2A.
Here’s an example of what an HTTP POST request to register a dynamic client might look like:


POST https://fhir.epic.com/interconnect-fhir-oauth/oauth2/register HTTP/1.1
Content-Type: application/json
Authorization: Bearer Nxfve4q3H9TKs5F5vf6kRYAZqzK7j9LHvrg1Bw7fU_07_FdV9aRzLCI1GxOn20LuO2Ahl5RkRnz-p8u1MeYWqA85T8s4Ce3LcgQqIwsTkI7wezBsMduPw_xkVtLzLU2O

{
    "software_id": "d45049c3-3441-40ef-ab4d-b9cd86a17225",
    "jwks": { 
        "keys": [{
                "e": "AQAB",
                "kty": "RSA",
                "n": "vGASMnWdI-ManPgJi5XeT15Uf1tgpaNBmxfa-_bKG6G1DDTsYBy2K1uubppWMcl8Ff_2oWe6wKDMx2-bvrQQkR1zcV96yOgNmfDXuSSR1y7xk1Kd-uUhvmIKk81UvKbKOnPetnO1IftpEBm5Llzy-1dN3kkJqFabFSd3ujqi2ZGuvxfouZ-S3lpTU3O6zxNR6oZEbP2BwECoBORL5cOWOu_pYJvALf0njmamRQ2FKKCC-pf0LBtACU9tbPgHorD3iDdis1_cvk16i9a3HE2h4Hei4-nDQRXfVgXLzgr7GdJf1ArR1y65LVWvtuwNf7BaxVkEae1qKVLa2RUeg8imuw",
            }
        ]
    }
}
The EHR stores your app's public key, issues it a dynamic client ID, and returns a response that might look like:


HTTP/1.1 201 Created
Content-Type: application/json

{
    "redirect_uris": [
        " https://fhir.epic.com/test/smart"
    ],
    "token_endpoint_auth_method": "none",
    "grant_types": [
        "urn:ietf:params:oauth:grant-type:jwt-bearer"
    ],
    "software_id": " d45049c3-3441-40ef-ab4d-b9cd86a17225",
    "client_id": "G65DA2AF4-1C91-11EC-9280-0050568B7514",
    "client_id_issued_at": 1632417134,
    "jwks": {
        "keys": [{
                "kty": "RSA",
                "n": "vGASMnWdI-ManPgJi5XeT15Uf1tgpaNBmxfa-_bKG6G1DDTsYBy2K1uubppWMcl8Ff_2oWe6wKDMx2-bvrQQkR1zcV96yOgNmfDXuSSR1y7xk1Kd-uUhvmIKk81UvKbKOnPetnO1IftpEBm5Llzy-1dN3kkJqFabFSd3ujqi2ZGuvxfouZ-S3lpTU3O6zxNR6oZEbP2BwECoBORL5cOWOu_pYJvALf0njmamRQ2FKKCC-pf0LBtACU9tbPgHorD3iDdis1_cvk16i9a3HE2h4Hei4-nDQRXfVgXLzgr7GdJf1ArR1y65LVWvtuwNf7BaxVkEae1qKVLa2RUeg8imuw",
                "e": "AQAB"
            }
        ]
    }
}
Step 3: Get an access token you can use to retrieve FHIR resources
Now that you have registered a dynamic client with its own credentials, there are two ways you can get an access token to make FHIR calls.  We recommend that you use the JWT bearer flow. In the JWT bearer flow, the client issues a JWT with its client ID as the "sub" (subject) claim, indicating the access token should be issued to the users who registered the client. It is also possible to use the SMART standalone launch sequence again to get a refresh token and then use the refresh token flow. Note that both flows involve your app making a JSON Web Token and signing it with its private key.

Generate a JSON Web Token
Your app follows the guidelines below to create a JWT assertion using its new private key.

To get an access token, your confidential app needs to authenticate itself.  Your dynamic client uses the private key it generated in step 2 to sign a JWT.

Here’s an example of the JWT body:


{
    "sub": "G00000000-0129-A6FA-7EDC-55B3FB6E85F8",
    "aud": "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token",
    "jti": "3fca7b08-e5a1-4476-9e4b-4e17f0ad7d1d",
    "nbf": 1639694983,
    "exp": 1639695283,
    "iat": 1639694983,
    "iss": "G00000000-0129-A6FA-7EDC-55B3FB6E85F8"
}
And here’s the final encoded JWT:

eyJhbGciOiJSUzI1NiIsImtpZCI6ImJXbGphR0ZsYkNBOE15QnNZWFZ5WVE9PSIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJHMDAwMDAwMDAtMDEyOS1BNkZBLTdFREMtNTVCM0ZCNkU4NUY4IiwiYXVkIjpbImh0dHBzOi8vdnMtaWN4LmVwaWMuY29tL0ludGVyY29ubmVjdC1DdXJyZW50LUZpbmFsLVByaW1hcnkvIl0sImp0aSI6IjNmY2E3YjA4LWU1YTEtNDQ3Ni05ZTRiLTRlMTdmMGFkN2QxZCIsIm5iZiI6MTYzOTY5NDk4MywiZXhwIjoxNjM5Njk1MjgzLCJpYXQiOjE2Mzk2OTQ5ODMsImlzcyI6IkcwMDAwMDAwMC0wMTI5LUE2RkEtN0VEQy01NUIzRkI2RTg1RjgifQ.UyW_--xpDdfB3EbxQ1KwRRuNDGIb034Y9mpExaaYyoVVkfz3ophzueIFMRrcdqTWmH96Ivx7O-fnjvHkb9iv1ELGVS_UYZy-JNb7r5VHDhdEYoRJzomYQzAyZutK9CJuJQZSvJeQLOXFoFN-fuCHIUBmSoTY5FDGy8gmq_a5fD_L-PnrXCD6SyP663s8kP-cFWh1iuXP0pjg8EMuFFEwgSo-chvv6RO4LIBebqkkv5qkgO_nrcXVJpxu42FDNrP2618q2Rw7sdIaewDw_I5026T4jNSoJXT12dHurqzedvC20exOO2MA6Vh1o2iVyzIfPE1EnEf-hk4WRFtQTUlqCQ
Step 3a: Get an access token using the JWT bearer flow
For the duration the user selected when approving your app to get an authorization code in step 1, your app can get an access token whenever it needs using the JWT bearer authorization grant described in RFC 7523 Section 2.1.

Recall that in the JWT bearer flow, the client issues a JWT to itself with a "sub" (subject) claim that indicates the user on whose behalf the client acts.  Because the dynamic client your app registered in step 2 is bound to the user who logged in during the SMART standalone launch sequence in step 1, the server only accepts a JWT where the subject is the user bound to that client.

Your app posts the JWT it issued itself in the Generate a JSON Web Token step to the server to get an access token. The following parameters are required in the POST body:

grant_type: This parameter contains the static value urn:ietf:params:oauth:grant-type:jwt-bearer.
assertion: This parameter contains the JWT your app generated above.
client_id: This parameter contains the dynamic client ID assigned in step 2.
Here’s an example of an HTTP POST request for an access token. You will replace the [assertion] and [client_id] placeholders with your own values.


POST https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token HTTP/1.1
Content-Type: application/x-www-form-urlencoded

grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer&assertion=[assertion]&client_id=[client_id]
The authorization server responds to the HTTP POST request with a JSON object that includes an access token. The response contains the following fields:

access_token: This parameter contains the access token issued by Epic to your application and is used in future requests.
See the Epic-Issued OAuth 2.0 Tokens appendix section for details on handling access tokens.
token_type: In Epic's OAuth 2.0 implementation, this parameter always includes the value bearer.
expires_in: This parameter contains the number of seconds for which the access token is valid.
epic.dstu2.patient: This parameter identifies the DSTU2 FHIR ID for the patient, if a patient is in context at time of launch.
scope: This parameter describes the access your application is authorized for.
patient: This parameter identifies provides the FHIR ID for the patient.
Note that you can include additional fields in the response if needed based on the integration configuration. For more information, refer to Launching your apptopic. Here's an example of what a JSON object including an access token might look like:


{
    "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJ1cm46R1RNUUFDVVI6Y2UuZ3RtcWFjdXIiLCJjbGllbnRfaWQiOiJHMDAwMDAwMDAtMDEyOS1BNkZBLTdFREMtNTVCM0ZCNkU4NUY4IiwiZXBpYy5lY2kiOiJ1cm46ZXBpYzpzMmN1cmd0IiwiZXBpYy5tZXRhZGF0YSI6ImVTMUF1dng4NlhRanRmVExub2loeks4QVRjdU5OUDFnRHhCRklvR0EyVUhHdlpDRE5PYjVZQ3NFZVhlUjExa1UyTjBHaHIwZjIwcE5yQnJ0V1JUa0l4d3VoVnlYeEVYUjQwVGlkdXNKdTk5ZmZRLWsybjFJWEY4X2I0SS11a054IiwiZXBpYy50b2tlbnR5cGUiOiJhY2Nlc3MiLCJleHAiOjE2Mzk2OTg1ODgsImlhdCI6MTYzOTY5NDk4OCwiaXNzIjoidXJuOkdUTVFBQ1VSOmNlLmd0bXFhY3VyIiwianRpIjoiYzQ1YzU4NjUtY2E3Ny00YWVlLTk3NDEtY2YzNzFiNDlhY2FkIiwibmJmIjoxNjM5Njk0OTg4LCJzdWIiOiJlRmdDY3E4cW1PeXY1b3FEcUFyUS5MQTMifQ.G0Z3PBv4ldpTqkjBjNUnvRYeVnNzT8qvLsGAVN8S9YibJGGCH_Txd6Ph1c9yB2hlQW3dw9IkaAvxxlUuclGMzmtyPXeo8wcWC07t_0vVasS-Ya9VjeDtR1hO8rcqEgV1DhKZ1jsEbzlRvKuZvONew0gL25ug6dOolNXcPcluzK6sxEyf2UoosX-W3nsU0iYZPJI-mf7lMEbsMUOSY8CR-77uBap3suxxHy03BwtkAXP0GwW0KSjOVe7_bsxX9k4DEhWyZuEOgDjEhONQFe2TeuWgUcI2KQeK5HjzmxN3dp56rCZ8zlhlukgw-C0F2IDbkZ5on7g7rl8lm29I7_kq9g",
    "token_type": "Bearer",
    "expires_in": 3600,
    "scope": "patient/Immunization.Read patient/Immunization.read patient/Patient.read patient/Practitioner.read patient/PractitionerRole.read launch/patient offline_access",
    "state": "oYK9nyFdUgTb1n_hMHZESDea",
    "patient": "eUYSU3eH0lceii-4SYNvpPw3",
    "__epic.dstu2.patient": "TJR7HfYCw58VnihLrp.axehccg-4IcjmZd3lw7Spm1F8B"
}
Step 3b: Alternate flow with refresh tokens
If you completed Step 3A, you do not need to complete this step. This is an alternate workflow to the JWT bearer flow. We strongly recommend that you use the JWT bearer flow above so you can provide a smoother user experience in which the user only needs to authenticate once. To get a refresh token, your app would need to go through the Standalone Launch sequence a second time. The first time (see Step 1: Get the access token you'll use to register a dynamic client) you were using the public app profile and weren't issued a refresh token.  Now that you have registered a dynamic client with its own credentials, you can use the confidential-asymmetric app profile.

Get an authorization code
This is the same as the Get an authorization code step from Step 1 except:

The client_id should be that of your dynamic client
Your token request will resemble a backend services grant, using the following parameters:
client_assertion – set to a JWT signed with your dynamic client’s private key
client_assertion_type – set to urn:ietf:params:oauth:client-assertion-type:jwt-bearer
An additional parameter per grant_type (code or refresh_token) described below
Note that the user will once again need to log in.

Exchange the authorization code for an access token
When your app makes this request to the token, it needs to authenticate itself to be issued a refresh token.  It uses the JWT it generated to authenticate itself per RFC 7523 section 2.2. This request will look like the JWT bearer request except the grant type is authorization_code instead of urn:ietf:params:oauth:grant-type:jwt-bearer and it includes the PKCE code verifier like the access token request you made before registering the dynamic client.

In response to this request, you’ll get an access token and a refresh token.

Use the refresh token to get subsequent access tokens
When the access token expires, your app can generate a new JWT and use the refresh token flow to get a new access token.  This request will look like the JWT bearer request except the grant type is refresh_token instead of urn:ietf:params:oauth:grant-type:jwt-bearer.

SMART Backend Services (Backend OAuth 2.0)
Contents

Building a Backend OAuth 2.0 App
Complete Required Epic Community Member Setup to Audit Access from Your Backend Application
Using a JWT to Obtain an Access Token for a Backend Service
Step 1: Creating the JWT
Step 2: POSTing the JWT to Token Endpoint to Obtain Access Token
Overview
Backend apps (i.e. apps without direct end user or patient interaction) can also use OAuth 2.0 authentication through the client_credentials OAuth 2.0 grant type. Epic's OAuth 2.0 implementation for backend services follows the SMART Backend Services: Authorization Guide, though it currently differs from that profile in some respects. Application vendors pre-register a public key for a given Epic community member on the Epic on FHIR website and then use the corresponding private key to sign a JSON Web Token (JWT) which is presented to the authorization server to obtain an access token.


Building a Backend OAuth 2.0 App
To use the client_credentials OAuth 2.0 grant type to authorize your backend application's access to patient information, two pieces of information need to be shared between the authorization server and your application:

Client ID: The client ID identifies your application to authentication servers within the Epic community and allows you to connect to any organization.
Public key: The public key is used to validate your signed JSON Web Token to confirm your identity.
You can register your application for access to both the sandbox and Epic organizations here. You'll provide information, including a JSON Web Key set URL (JWK Set URL or JKU) that hosts a public key used to verify the JWT signature. Epic will generate a client ID for you. Your app will need to have both the Backend Systems radio button selected and the Use OAuth 2.0 box checked in order to register a JKU for backend OAuth 2.0.

Complete Required Epic Community Member Setup to Audit Access from Your Backend Application
Note: This build is not needed in the sandbox. The sandbox automatically maps your client to a user, removing the need for this setup.

When performing setup with an Epic community member, their Epic Client Systems Administrator (ECSA) will need to map your client ID to an Epic user account that will be used for auditing web service calls made by your backend application. Your app will not be able to obtain an access token until this build is completed.

Using a JWT to Obtain an Access Token for a Backend Service
You will generate a one-time use JSON Web Token (JWT) to authenticate your app to the authorization server and obtain an access token that can be used to authenticate your app's web service calls. There are several libraries for creating JWTs. See jwt.io for some examples.

Step 1: Creating the JWT
See the Creating a Public Private Key Pair for JWT Signature and the Creating a JWT sections for details on how to create a signed JWT.

Step 2: POSTing the JWT to Token Endpoint to Obtain Access Token
Your application makes a HTTP POST request to the authorization server's OAuth 2.0 token endpoint to obtain access token. The following form-urlencoded parameters are required in the POST body:

grant_type: This should be set to client_credentials.
client_assertion_type: This should be set to urn:ietf:params:oauth:client-assertion-type:jwt-bearer.
client_assertion: This should be set to the JWT you created above.
Here is an example request:

POST https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token HTTP/1.1
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&client_assertion_type=urn%3Aietf%3Aparams%3Aoauth%3Aclient-assertion-type%3Ajwt-bearer&client_assertion=eyJhbGciOiJSUzM4NCIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJkNDUwNDljMy0zNDQxLTQwZWYtYWI0ZC1iOWNkODZhMTcyMjUiLCJzdWIiOiJkNDUwNDljMy0zNDQxLTQwZWYtYWI0ZC1iOWNkODZhMTcyMjUiLCJhdWQiOiJodHRwczovL2ZoaXIuZXBpYy5jb20vaW50ZXJjb25uZWN0LWZoaXItb2F1dGgvb2F1dGgyL3Rva2VuIiwianRpIjoiZjllYWFmYmEtMmU0OS0xMWVhLTg4ODAtNWNlMGM1YWVlNjc5IiwiZXhwIjoxNTgzNTI0NDAyLCJuYmYiOjE1ODM1MjQxMDIsImlhdCI6MTU4MzUyNDEwMn0.dztrzHo9RRwNRaB32QxYLaa9CcIMoOePRCbpqsRKgyJmBOGb9acnEZARaCzRDGQrXccAQ9-syuxz5QRMHda0S3VbqM2KX0VRh9GfqG3WJBizp11Lzvc2qiUPr9i9CqjtqiwAbkME40tioIJMC6DKvxxjuS-St5pZbSHR-kjn3ex2iwUJgPbCfv8cJmt19dHctixFR6OG-YB6lFXXpNP8XnL7g85yLOYoQcwofN0k8qK8h4uh8axTPC21fv21mCt50gx59XgKsszysZnMDt8OG_G4gjk_8JnGHwOVkJhqj5oeg_GdmBhQ4UPuxt3YvCOTW9S2vMikNUnxrhdVvn2GVg
And here is an example response body assuming the authorization server approves the request:

{
"access_token": "i82fGhXNxmidCt0OdjYttm2x0cOKU1ZbN6Y_-zBvt2kw3xn-MY3gY4lOXPee6iKPw3JncYBT1Y-kdPpBYl-lsmUlA4x5dUVC1qbjEi1OHfe_Oa-VRUAeabnMLjYgKI7b",
"token_type": "bearer",
"expires_in": 3600,
"scope": "Patient.read Patient.search"
}
Note: See the Epic-Issued OAuth 2.0 Tokens appendix section for details on handling access tokens.
JSON Web Tokens (JWTs)
Contents

Creating a Public Private Key Pair for JWT Signature
OpenSSL
Windows PowerShell
Finding the Public Key Certificate Fingerprint (Also Called Thumbprint)
Creating a JWT
JSON Web Key Sets
Key Identifier Requirements
Hosting a JWK Set URL
App-Level vs Licensing Specific JWK Set URLs
Registering a JWK Set URL
Key Rotation
Providing Multiple Public Keys
How
Why Not?
Use Cases
Background
JSON Web Tokens (JWTs) can be used for some OAuth 2.0 workflows. JWTs are required to be used by the client credentials flow used by backend services, and can be used, as an alternative to client secrets, for apps that use the confidential client profile or refresh tokens. You will generate a one-time use JWT to authenticate your app to the authorization server and obtain an access token that can be used to authenticate your app's web service calls, and potentially a refresh token that can be used to get another access token without a user needing to authorize the request. There are several libraries for creating JWTs. See jwt.io for some examples.
Creating a Public Private Key Pair for JWT Signature
There are several tools you can use to create a key pair. As long as you can export your public key to a base64 encoded X.509 certificate (backend clients) or JSON Web Key Set (frontend confidential clients) for registration on the Epic on FHIR website, or you can host it on a properly formatted JWK Set URL, the tool you use to create the key pair and file format used to store the keys is not important. If your app is hosted by Epic community members ("on-prem" hosting) instead of cloud hosted, you should have unique key pairs for each Epic community member you integrate with. In addition, you should always use unique key pairs for non-production and production systems.

Here are examples of two tools commonly used to generate key pairs:

Creating a Public Private Key Pair: OpenSSL
You can create a new private key named privatekey.pem using OpenSSL with the following command:

openssl genrsa -out /path_to_key/privatekey.pem 2048

Make sure the key length is at least 2048 bits.

For backend apps, you can export the public key to a base64 encoded X.509 certificate named publickey509.pem using this command:

openssl req -new -x509 -key /path_to_key/privatekey.pem -out /path_to_key/publickey509.pem -subj '/CN=myapp'

Where '/CN=myapp' is the subject name (for example the app name) the key pair is for. The subject name does not have a functional impact in this case but it is required for creating an X.509 certificate.

For frontend confidential clients, refer to JSON Web Key Sets.

Creating a Public Private Key Pair: Windows PowerShell
You can create a key pair using Windows PowerShell with this command, making sure to run PowerShell as an administrator:

New-SelfSignedCertificate -Subject "MyApp"

Note that the Epic on FHIR website is extracting the public key from the certificate and discarding the rest of the certificate information, so it's not 'trusting' the self-signed certificate per se.

The subject name does not have a functional impact in this case, but it is required for creating an X.509 certificate. Note that this is only applicable to backend apps. For frontend confidential clients, refer to JSON Web Key Sets.

You can export the public key using either PowerShell or Microsoft Management Console.

If you want to export the public key using PowerShell, take note of the certificate thumbprint and storage location printed when you executed the New-SelfSignedCertificate command.

PS C:\dir> New-SelfSignedCertificate -Subject "MyApp"

PSParentPath: Microsoft.PowerShell.Security\Certificate::LocalMachine\MY

Thumbprint                                Subject
----------                                -------
3C4A558635D67F631E5E4BFDF28AE59B2E4421BA  CN=MyApp
Then export the public key to a X.509 certificate using the following commands (using the thumbprint and certificate location from the above example):

PS C:\dir> $cert = Get-ChildItem -Path Cert:\LocalMachine\My\3C4A558635D67F631E5E4BFDF28AE59B2E4421BA

PS C:\dir> Export-Certificate -Cert $cert -FilePath newpubkeypowerShell.cer

Export the binary certificate to a base64 encoded certificate:

PS C:\dir> certutil.exe -encode newpubkeypowerShell.cer newpubkeybase64.cer

If you want to export the public key using Microsoft Management Console, follow these steps:

Run (Windows + R) > mmc (Microsoft Management Console).
Go to File > Add/Remove SnapIn.
Choose Certificates > Computer Account > Local Computer. The exact location here depends on the certificate store that was used to create and store the keys when you ran the New-SelfSignedCertificate PowerShell command above. The store used is displayed in the printout after the command completes.
Then back in the main program screen, go to Personal > Certificates and find the key pair you just created in step 1. The "Issue To" column will equal the value passed to -Subject during key creation (e.g. "MyApp" above).
Right click on the certificate > All Tasks > Export.
Choose option to not export the private key.
Choose to export in base-64 encoded X.509 (.CER) format.
Choose a file location.
Finding the Public Key Certificate Fingerprint (Also Called Thumbprint)
The public key certificate fingerprint (also known as thumbprint in Windows software) is displayed for JWT signing public key certificates that are uploaded to the Epic on FHIR website. There are a few ways you can find the fingerprint for a public key certificate:

If you created the public key certificate using Windows PowerShell using the steps above, the thumbprint was displayed after completing the command. You can also print public keys and their thumbprints for a given certificate storage location using the Get-ChildItem PowerShell command.
For example, run Get-ChildItem -Path Cert:\LocalMachine\My to find all certificate thumbprints in the local machine storage.

You can follow the steps here to find the thumbprint of a certificate in Microsoft Management Console.
You can run this OpenSSL command to print the public key certificate fingerprint that would be displayed on the Epic on FHIR website, replacing openssl_publickey.cert with the name of your public key certificate:
$ openssl x509 -noout -fingerprint -sha1 -inform pem -in openssl_publickey.cert

Note that the output from this command includes colons between bytes which are not shown on the Epic on FHIR website.

Creating a JWT
The JWT should have these headers:

Header	Description
alg	The JWT authentication algorithm. Epic supports the following RSA signing algorithms for all confidential clients: RS256, RS384, and RS512. For clients that register a JSON Web Key Set URL, Epic also supports the following Elliptic Curve algorithms: ES256, ES384. Epic does not support manual upload of Elliptic Curve public keys, and we recommend new apps use a JWK Set URL and Elliptic Curve keys.
typ	If provided, this should always be set to JWT.
kid	For apps using JSON Web Key Sets (including dynamically registed clients), set this value to the kid of the target public key from your key set
jku	For apps using JSON Web Key Set URLs, optionally set this value to the URL you registered on your application
The JWT header should be formatted as follows:

{
"alg": "RS384",
"typ": "JWT"
}
The JWT should have these claims in the payload:

Claim	Description	Remarks
iss	Issuer of the JWT. This is the app's client_id, as determined during registration on the Epic on FHIR website, or the client_id returned during a dynamic registration	This is the same as the value for the sub claim.
sub	Issuer of the JWT. This is the app's client_id, as determined during registration on the Epic on FHIR website, or the client_id returned during a dynamic registration	This is the same as the value for the iss claim.
aud	The FHIR authorization server's token endpoint URL. This is the same URL to which this authentication JWT will be posted. See below for an example POST.	It's possible that Epic community member systems will route web service traffic through a proxy server, in which case the URL the JWT is posted to is not known to the authorization server, and the JWT will be rejected. For such cases, Epic community member administrators can add additional audience URLs to the allowlist, in addition to the FHIR server token URL if needed.
jti	A unique identifier for the JWT.	The jti must be no longer than 151 characters and cannot be reused during the JWT's validity period, i.e., before the exp time is reached. In the November 2024 version of Epic and later, this value must be a string.
exp	Expiration time integer for this authentication JWT, expressed in seconds since the "Epoch" (1970-01-01T00:00:00Z UTC).	The exp value must be in the future and can be no more than 5 minutes in the future at the time the access token request is received.
nbf	Time integer before which the JWT must not be accepted for processing, expressed in seconds since the "Epoch" (1970-01-01T00:00:00Z UTC).	The nbf value cannot be in the future, cannot be more recent than the exp value, and the exp - nbf difference cannot be greater than 5 minutes.
iat	Time integer for when the JWT was created, expressed in seconds since the "Epoch" (1970-01-01T00:00:00Z UTC).	The iat value cannot be in the future, and the exp - iat difference cannot be greater than 5 minutes.
Here's an example JWT payload:

{
"iss": "d45049c3-3441-40ef-ab4d-b9cd86a17225",
"sub": "d45049c3-3441-40ef-ab4d-b9cd86a17225",
"aud": "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token",
"jti": "f9eaafba-2e49-11ea-8880-5ce0c5aee679",
"exp": 1583524402,
"nbf": 1583524102,
"iat": 1583524102
}
The header and payload are then base64 URL encoded, combined with a period separating them, and cryptographically signed using the private key to generate a signature. Conceptually:

signature = RSA-SHA384(base64urlEncoding(header) + '.' + base64urlEncoding(payload), privatekey)
The full JWT is constructed by combining the header, body and signature as follows:

base64urlEncoding(header) + '.' + base64urlEncoding(payload) + '.' + base64urlEncoding(signature)
A fully constructed JWT looks something like this:

eyJhbGciOiJSUzM4NCJ9.eyJpYXQiOjE3MDc0MjQzMzYsImlzcyI6IjAxZjBlMzllLTIyY2MtNGFiNS05NTE0LWMyN2Y5Mzg0NzFjOCIsInN1YiI6IjAxZjBlMzllLTIyY2MtNGFiNS05NTE0LWMyN2Y5Mzg0NzFjOCIsImF1ZCI6Imh0dHBzOi8vdmVuZG9yc2VydmljZXMuZXBpYy5jb20vaW50ZXJjb25uZWN0LWFtY3VycHJkLW9hdXRoL29hdXRoMi90b2tlbiIsImV4cCI6MTcwNzQyNDYzNiwianRpIjoiMGIyZjZmMTQtMThkZS01NTU1LWJkMjUtZTNkMzg0ZmEwZTVkIn0.hE8DAq72XjJWNci5JFEuN5TrLh9W1UZP4H904GTIhggZNnNxtJLvUPKPrpf9PYgMZmgHb6peVR5MMUnQRtFHLZsH_C2v9ridfIA8BgWBL5eNiXcriUM9rIEvHwImgbKyPQUY_a0D7BCXiLqdjMAdEZe_afxCQBW0I7EsGqbpA0agayhLIDrlhcfCtdBrGyBlwW2zlUjTUo8Rj2o59tL90w6mVykeZIsJfcLQF4jeSfNOko-908mha_Gga6szWCqxlCr5ed9i6mjRSUQByG-GAFnCIhPULeedCHEgb9WF2NC0cImjK92jGSM6i43Y19uHvCFYMEkBMDaDK7WQigm3yg
JSON Web Key Sets
Applications using JSON Web Token (JWT) authentication can provide their public keys to Epic as a JSON Web Key (JWK) Set. Epic accepts keys of type RSA or EC. EC is only support for JWKS returned from a JWKS URL and is not supported for static JWKS uploaded directly. When using a JWKS URL we recommend including the kid values in your keys and in the headers of your assertions. Note that when uploading a static JWKS directly, only the "kty", "e" and "n" properties will be saved from the uploaded keys. Other fields typically present in a JWKS like "kid" or "alg" can exist in the uploaded JWKS without an error but they will be discarded upon save.

In the example key set below, the "RSA" key can be used with the RS256, RS384 or RS512 signing algorithms. The "EC" key can only be used with the "ES384" algorithm because it specifies a curve of P-384. The algorithm is determined when you first generate the key, like in the example above.

        {
            "keys": [
                { "kty":"RSA", "e": "AQAB", "kid": "d1fc1715-3299-43ec-b5de-f943803314c2", "n": "uPkpNCkqbbismKNwKguhL0P4Q40sbyUkUFcmDAACqBntWerfjv9VzC3cAQjwh3NpJyRKf7JvwxrbELvPRMRsXefuEpafHfNAwj3acTE8xDRSXcwzQwd7YIHmyXzwHDfmOSYW7baAJt-g_FiqCV0809M9ePkTwNvjpb6tlJu6AvrNHq8rVn1cwvZLIG6KLCTY-EHxNzsBblJYrZ5YgR9sfBDo7R-YjE8c761PSrBmUM4CAQHtQu_w2qa7QVaowFwcOkeqlSxZcqqj8evsmRfqJWoCgAAYeRIsgKClZaY5KC1sYHIlLs2cp2QXgi7rb5yLUVBwpSWM4AWJ_J5ziGZBSQYB4sWWn8bjc5-k1JpUnf88-UVZv9vrrkMJjNam32Z6FNm4g49gCVu_TH5M83_pkrsNWwCu1JquY9Z-eVNCsU_AWPgHeVZyXT6giHXZv_ogMWSh-3opMt9dzPwYseG9gTPXqDeKRNWFEm46X1zpcjh-sD-8WcAlgaEES6ys_O8Z" },
                { "kty":"EC", "kid": "iTqXXI0zbAnJCKDaobfhkM1f-6rMSpTfyZMRp_2tKI8", "crv": "P-384", "x": "C1uWSXj2czCDwMTLWV5BFmwxdM6PX9p-Pk9Yf9rIf374m5XP1U8q79dBhLSIuaoj", "y": "svOT39UUcPJROSD1FqYLued0rXiooIii1D3jaW6pmGVJFhodzC31cy5sfOYotrzF" }
            ]
        }	
    
Key Identifier Requirements
Epic recommends your application provide the kid field in JWK Sets and in your JWT Headers when using a JWKS URL, since Epic can use the identifier to find your intended key. Epic does not require your key identifiers to be thumbprints, and will accept any value that is unique within your key set.

Hosting a JWK Set URL
Starting in the February 2024 version of Epic, customers can require back-end apps using JWT authentication to use a JSON Web Key Set URL to provide public keys to Epic for JWT verification. JWK Set URLs streamline implementation and make key rotation feasible by providing a centralized and trusted place where Epic community members can retrieve your public keys.

App-Level vs Licensing Specific JWK Set URLs
By default, every community member will use the app-level JWK Set URLs when validating your application's JWTs. These are the URLs you provide when building your application. Re-using these default URLs for all your integrations is appropriate for cloud-based apps that can re-use a single private key (without making a copy).

However, if your application is hosted by Epic community members ("on-prem", applications), then you should instead provide different JWK Set URLs for every licensed community member. There are 2 reasons on-prem applications should use distinct URLs:

These applications require physically separate servers, and cannot share a private key across installations without copying and transporting the key (a security risk)
Attempting to aggregate multiple public keys behind one URL is a security risk if those keys are in physically different places. If any one of your server environments is compromised, it can be used to impersonate any other instance of your application
Registering a JWK Set URL
When building or licensing an application that will authenticate against Epic, you are prompted to optionally upload non-production and production JWK Set URLs to your app. When registering these URLs, be sure of the following:

Are secured with TLS
Are publicly accessible
Do not require authentication
Will not change over time
Are responsive
Epic will verify points 1-3 whenever you provide a JWK Set URL

Note that there are separate non-production and production URLs because we recommend you use separate key sets for each.

Key Rotation
Before rotating your keys, remove any static public keys from your existing downloads

One benefit of JWK Set URLs is that your application can rotate its key as needed, and Epic can dynamically fetch the updated keys. It is a best practice to periodically rotate your private keys, and if you choose to do so, we recommend the following strategy:

Create your new public-private key pair ahead of time
Add your new public key to your JWK Set in addition to the existing one
Start using your new private key for signing JWTs
Once you are certain your system is no longer using the old private key, wait 5 minutes (the maximum JWT expiration time) remove the old public key from your JWK Set
In between steps 3 and 4, Epic will notice you are using a new private key and will automatically fetch the new key set. Every time you present a JWT to Epic we will check your JWK Set URL at most once, and only if the cached keys are expired or did not verify your JWT

Epic's default and maximum cache time is 29 hours, but your endpoint can override the default by using the Cache-Control HTTP response header. This is most useful during development and testing when you may want to update your non-production public keys ad-hoc, or to test the availability of your server from Epic. You could for instance respond with "Cache-Control": "no-store" to stop Epic from storing your keys at all. This is not recommended for production usage since you lose the performance benefits of caching.

Providing Multiple Public Keys
How
Apps can provide multiple public keys to an Epic community member by providing a JWK Set URL that contains multiple keys.

Why Not?
In general, the only reason to provide multiple public keys is if your system spans multiple separate servers or cloud environments, and so you cannot share a private key between them. If you can re-use a key without making copies of it, then you should re-use that key and focus on protecting it with the best policy available (For example, using your hosting provider's key store or using a Trusted Platform Module).

Use Cases
Example use cases:

Having multiple isolated testing environments, where you may provide multiple non-production public keys (one for each environment)
On-premises applications with multiple servers hosted by a given community member. In this case you would provide multiple production public keys (one for each server)
Appendix
Epic-Issued OAuth 2.0 Tokens
Starting in the May 2020 version of Epic, Epic community members can enable a feature that makes all OAuth 2.0 tokens and codes into JSON Web Tokens (JWTs) instead of opaque tokens. This feature increases the length of these tokens significantly and is enabled in the fhir.epic.com sandbox. Developers should ensure that app URL handling does not truncate OAuth 2.0 tokens and codes.

The format of these tokens is helpful for troubleshooting, but Epic strongly recommends against relying on these tokens being JWTs. This same feature can be turned off by Epic community members, and Epic may need to change the format of these tokens in the future.

In general, if the "aud" parameter of a JWT is not your app's client ID, you should not be decoding it programmatically. For the 5 types of JWTs mentioned in this tutorial, here's a breakdown of their audience (aud) and issuers (iss):

JWT Scenario	Audience (aud)	Issuer (iss)
Launch Token	Authorization server	Authorization server
Authorization Code	Authorization server	Authorization server
Access Token	Authorization server	Authorization server
Openid Connect ID Token	The app's client_id	Authorization server
Client Assertion	Authorization server	The app's client_id
Trusting an OAuth 2.0 Token
A common question that developers ask is how an app can "trust" an OAuth 2.0 token without cryptographically verifying it. Our answer is that your app should never trust a token by itself and should rely on the authorization server to verify a given token. When redeeming an authorization code for an access token, your app can trust that if the request succeeded that the authorization code was valid, and you can then create a session in your application. The only exception is an openid connect id_token, which is designed to be verified by the client application.

Epic-Issued OAuth 2.0 Tokens
Starting in the May 2020 Epic version, Epic community members can enable a feature that makes all OAuth 2.0 tokens and codes into JSON Web Tokens (JWTs) instead of opaque tokens. This feature increases the length of these tokens significantly and is enabled in the vendorservices.epic.com sandbox. Developers should ensure that app URL handling does not truncate OAuth 2.0 tokens and codes.

The format of these tokens is helpful for troubleshooting, but Epic strongly recommends against relying on these tokens being JWTs. This same feature can be turned off by Epic community members, and Epic may need to change the format of these tokens in the future.

In general, if the "aud" parameter of a JWT is not your app's client ID, you should not be decoding it programmatically. For the 5 types of JWTs mentioned in this tutorial, here's a breakdown of their audience (aud) and issuers (iss):

JWT Scenario	Audience (aud)	Issuer (iss)
Launch Token	Authorization server	Authorization server
Authorization Code	Authorization server	Authorization server
Access Token	Authorization server	Authorization server
Openid Connect ID Token	The app's client_id	Authorization server
Client Assertion	Authorization server	The app's client_id
Trusting an OAuth 2.0 Token
A common question that developers ask is how an app can "trust" an OAuth 2.0 token without cryptographically verifying it. Our answer is that your app should never trust a token by itself and should rely on the authorization server to verify a given token. When redeeming an authorization code for an access token, your app can trust that if the request succeeded that the authorization code was valid, and you can then create a session in your application. The only exception is an openid connect id_token, which is designed to be verified by the client application.

How you handle the authorization code is the most important step in an OAuth 2.0 flow. See our best practice for using this step to secure your application.

Refresh Tokens and Persistent Access Periods
The time during which a client can use refresh tokens to get new access is known as the persistent access period. In patient-facing contexts, it can be set by the patient through MyChart. In non-patient-facing contexts, the duration will be set by the refresh token itself. Specifically, the start of the period is set to the time the token is provisioned and the end of the period is set to the token's expiration date-time.

In many situations, only one access token will want to be requested with the original refresh token and the persistent access period just defines when the that refresh token can do so. However, a client will often need access over a longer period of time. In these situations, a single refresh token won't be an efficient solution as a new authorization request will have to be made after the token is used or the period ends. There are two workflows for getting an extended persistent access period by utilizing multiple refresh tokens: rolling refresh tokens and indefinite access.

Rolling Refresh Persistent Access Periods
In this workflow, multiple refresh tokens are used to have the persistent access period last as long as a single refresh token could. A first refresh token is provisioned and the persistent access period is set as normal (i.e., start of period = time of provisioning and end of period = token expiration date-time). This first refresh token can then be used in another access token request that specifies to return a refresh token. The refresh token granted from this access token request will be generated normally except for the fact that its expiration date-time will be set to the same as the first refresh token. All subsequent refresh tokens in the workflow will also have this same expiration date-time.

This means that the persistent access period of a rolling refresh workflow is defined by the first refresh token and all subsequent refresh tokens 'fall within' that period. The below diagram gives a visual representation of the persistent access period during a rolling refresh token workflow.

For patient-facing apps, the length of the persistent access period for a rolling refresh will be set by each patient during the OAuth 2.0 flow. They can choose from a variety of options (e.g., 1 hours, 1 day, 1 week, …) configured by the customer.

To enable rolling refresh access for non-patient-facing apps, check that your customers have properly configured their external client record.


Indefinite Persistent Access Periods 
In this workflow, the persistent access period lasts indefinitely. It does so by using consecutive refresh tokens like in rolling refresh workflows. The notable difference is that, here, new refresh tokens have an expiration date-time greater than the one before it. In the rolling refresh workflow, this is always set to that of the first token. Since the persistent access period end date-time is set by the token's expiration, continually setting new refresh tokens to expire in the future will make the persistent access period last until no more refresh tokens are requested.

To enable indefinite access for patient-facing apps, instruct your customers to follow these configuration steps. Note that this only gives patients the option of indefinite access. Each patient still chooses their max access period.

Navigate to Login and Access Configuration in MyChart.
Navigate to OAuth Access Duration Configuration.
Specify 'Indefinite' in the Global Max OAuth Access Duration field.
To enable indefinite access for non-patient-facing apps, check that your customers have properly configured their external client records.


Limit Use of Localhost URIs
Launched applications must register a list of URLs that Epic will use as an allowlist during OAuth 2.0. Epic will only deliver authorization codes to a URL that is listed on the corresponding app.

As a security best practice, apps should not include localhost/loopback URIs in this list. An exception is for Native applications which are designed to use localhost for the redirect, such as certain libraries available from the AppAuth group. An alternative available for native apps are platform specific link associations, discussed in our Considerations for Native Apps below.

If your developers wish to use localhost URIs for testing in our sandboxes, we recommend creating a second test application that will never be activated in customer environments and listing your localhost URLs there.

Considerations for Native Apps
Additional security considerations must be taken into account when launching a native app to sufficiently protect the authorization code from malicious apps running on the same device. There are a few options for how to implement this additional layer of security:

Platform-specific link association: Android, iOS, Windows, and other platforms have introduced a method by which a native app can claim an HTTPS redirect URL, demonstrate ownership of that URL, and instruct the OS to invoke the app when that specific HTTPS URL is navigated to. Apple's iOS calls this feature "Universal Links"; Android, "App Links"; Windows, "App URI Handlers". This association of an HTTPS URL to native app is platform-specific and only available on some platforms.
Proof Key for Code Exchange (PKCE): This is a standardized, cross-platform technique for public clients to mitigate the threat of authorization code interception. However, it requires additional support from the authorization server and app. PKCE is described in IETF RFC 7636 and supported starting in the August 2019 version of Epic. Note that the Epic implementation of this standard uses the S256 code_challenge_method. The "plain" method is not supported.
Starting in the August 2019 version of Epic, the Epic implementation of OAuth 2.0 supports PKCE and Epic recommends using PKCE for native mobile app integrations. For earlier versions or in cases where PKCE cannot be used, Epic recommends the use of Universal Links/App Links in lieu of custom redirect URL protocol schemes.

Subspace Security Considerations
This section applies to certain applications with a user type of "Backend Systems". If your application does not fit this criterion, you can skip this section. You can also skip this section if your Backend application does not use Subspace APIs; in which case you should remove the "Subspace" functionality and un-check the "Can Register Dynamic Clients" checkbox.

Beginning March 2, 2023, Epic no longer supports registering new client IDs with the following combination of settings:

User type of Backend Systems

Uses OAuth 2.0

Functionality: Subspace

Registers Dynamic Clients

Functionality: Incoming Web Services

The combination of settings 1-4 has historically been used for integration with Epic's Subspace Communication Framework. In this approach your application registers workstation-specific private keys to authorize Subspace API calls.

As a security best practice, for integrations using the above settings, instead it is recommended to authenticate the Incoming Web Services (Setting 5) using the OAuth 2.0 token obtained from a SMART on FHIR app launch or configuring your integration to use a multi-context application.

When a workstation-specific private key is allowed to authorize web service calls, a user may be able to bypass user-specific authentication and authorization checks within the web services themselves. This risk is mitigated in virtualized environments where the workstation (and the private key) is controlled by administrators. These security implications do not apply to Subspace APIs as Subspace APIs provide access to the Epic database only after the user has authenticated against Epic.

As a security best practice, rather than using the combination of settings above, an application that needs all these features (particularly web services) can do one of the following:

SMART App Launch
We recommend following the FHIRcast specification's guidance, which says to use the SMART App Launch to secure communication. One reason to use the SMART App Launch for Subspace integrations is that the launch provides user-specific security. The token provided by the launch is designed for end-users to use directly and provides the flexibility for you to call web services from any portion of your infrastructure.

Per the FHIRcast specification, the hub needs to launch your application before you can use Subspace APIs. Practically, this means your end users need to launch your application from Epic to begin their workflow. Epic's "User Toolbar" launch approach provides the ability for the user to launch your application before opening any patient and provides your application with authorization to view multiple patients' charts without re-launching. This requires coordination with the Epic Community Member to show the launch button to end users and requires instructing end users to start their workflow in this way.

By default, launched Subspace applications will receive 1 hour of API authorization per launch. If your application requires longer workflows, we offer the following options:

Epic offers a Dynamic Client Registration (DCR) workflow where you can register a temporary and in-memory private key to extend your application's access. Epic will revoke the key's access after a period of inactivity, so you should request a new access token before the most recent one expires. After the end user closes your application, you should delete the private key and Epic will revoke its access due to inactivity.

Note this workflow differs from the "Backend System" DCR workflow above, in that tokens issued to the client are tied to the user who launched the application. In this way, Epic can conduct user-specific security checks when your application calls web services.

(Not recommended) Epic Community Members can extend the default duration of your access tokens to any value, for example 4 hours.

Multi-Context Application
In this approach, your application handles the burden of authenticating the end-user and mediating their access to the Epic database. This can only be done securely by using server-side controls; safeguards put in place in a client-application (example: a native desktop app) are not sufficient, as they could potentially be bypassed by an end user.

An existing "Backend System" Subspace integration can achieve this with the following:

Created a new client ID with the following settings:

User type of Backend Systems

Uses OAuth 2.0

Feature: Incoming API

Select your required Web Services

Conduct Backend OAuth 2.0 as you did with your existing app, but skip the DCR step

Follow our security best practices for Backend applications, which solve the user-authentication issues above

SMART Scopes
SMART scopes are returned in the scope parameter of the OAuth 2.0 token endpoint response and determine which resources an application has permission to access and what actions the application is permitted to take. The scopes provided are based on the scopes that your app requested in your authorize request as well as the incoming APIs you have selected on your app page.

As of the August 2024 version of Epic, both SMART v1 and SMART v2 scope formatting are supported. Prior to the August 2024 version, only SMART v1 scopes are supported.

The actions defined by SMART v1 scopes are .read and .write. SMART v2 scopes use CRUDS syntax and actions include: .c – create, .r – read, .u – update, .d – delete, and .s – search.

For example, the Observation.Create resource corresponds to either:

SMART v1: {user-type}/Observation.write
SMART v2: {user-type}/Observation.c
Which version should you select?
If your app uses SMART v1 scopes or if your app does not use SMART scopes at all, you should select SMART v1.

If your app uses SMART v2 scopes, you should select SMART v2.

Note: Prior to the August 2024 version of Epic, SMART v1 scope formatting will be returned regardless of the SMART Scope Version selected on your app page. If your app uses SMART scopes and your customer is on a version of Epic earlier than August 2024, you must support SMART v1 scopes.

Non-OAuth 2.0 Authentication
Epic supports forms of authentication in addition to OAuth 2.0. Only use these forms of authentication if OAuth 2.0 is not an option.
HTTP Basic Authentication 
HTTP Basic Authentication requires that Epic community members provision a username and password that your application will provide to the web server to authenticate every request.

Epic supports HTTP Basic Authentication via a system-level user record created within Epic's database. You may hear this referred to as an EMP record. You will need to work with an organization's Epic user security team to have a username and password provided to you.

When calling Epic's web services with HTTP Basic Authentication the username must be provided as follows: emp$<username>. Replace <username> with the username provided by the organization during implementation of your application.

Base64 encode your application's credentials and pass them in the HTTP Authorization header. For example, if you've been given a system-level username/password combination that is username/Pa$$w0rd1, the Authorization header would have a value of ZW1wJHVzZXJuYW1lOlBhJCR3MHJkMQ== (the base64 encoded version of emp$username:Pa$$w0rd1):

GET http://localhost:8888/website HTTP/1.1
Host: localhost:8888
Proxy-Connection: keep-alive
Authorization: Basic ZW1wJHVzZXJuYW1lOlBhJCR3MHJkMQ==
Storing HTTP Basic Authentication Values
The username and password you use to authenticate your web service requests are extremely sensitive since they can be used to pull PHI out of an Epic organization's system. The credentials should always be encrypted and should not be stored directly within your client's code. You should make sure that access to decrypt the credentials should be limited to only the users that need access to it. For example, if a service account submits the web service requests, only that service account should be able to decrypt the credentials.

Client Certificates and SAML tokens
Epic also supports the use of Client Certificates and SAML tokens as an authentication mechanism for server-to-server web service requests. We do not prefer these methods because both require web server administrators to maintain a trusted certificate for authentication. As certificates expire or servers need to be moved around, this puts an additional burden on system administrators.

Additional Required Headers
When you use OAuth 2.0 authentication, Epic can automatically gather important information about the client making a web service request. When you use a non-OAuth 2.0 authentication mechanism, we require that this additional information be passed in an HTTP header.

Epic-Client-ID
This is the client ID you were given upon your app's creation on the Epic on FHIR site. This is always required when calling Epic's web services if your app doesn't use OAuth 2.0 authentication.

GET http://localhost:8888/website HTTP/1.1
Host: localhost:8888
Proxy-Connection: keep-alive
Authorization: Basic ZW1wJHVzZXJuYW1lOlBhJCR3MHJkMQ==
Epic-Client-ID: 0000-0000-0000-0000-0000
Epic-User-ID and Epic-User-IDType
This is required for auditing requests to FHIR resources. The Epic-User-ID corresponds to an EMP (Epic User) account that an organization creates for your application. This might be required depending on the web services you are calling. The Epic-User-IDType is almost always EXTERNAL.

GET http://localhost:8888/website HTTP/1.1
Host: localhost:8888
Proxy-Connection: keep-alive
Authorization: Basic ZW1wJHVzZXJuYW1lOlBhJCR3MHJkMQ==
Epic-Client-ID: 0000-0000-0000-0000-0000					 	
Epic-User-ID: username					 	
Epic-User-IDType: EXTERNAL
We use cookies to improve our website. By accepting, you will receive these cookies from Epic on FHIR. Decline if you wish to use Epic on FHIR without these cookies. Read our privacy policy here.


Frequently Asked Questions (FAQs) Contact Terms of Use Privacy Policy
1979 Milky Way, Verona, WI 53593
© 1979-2025 Epic Systems Corporation. All rights reserved. Protected by U.S. patents. For details visit www.epic.com/patents.
HL7®, FHIR® and the FLAME mark are the registered trademarks of HL7 and are used with the permission of HL7. The use of these trademarks does not constitute a product endorsement by HL7.
Epic, open.epic, and Epic on FHIR are trademarks or registered trademarks of Epic Systems Corporation.

ID Types for APIs
Table of Contents
FHIR API IDs and HL7 OIDs
Identifier Type
Examples
Identifier System
Organization-Specific IDs and Value Sets
FHIR API IDs and HL7 OIDs
Epic’s FHIR APIs often use object identifiers (OIDs) to uniquely identify and exchange information about particular entities. An OID is a global, unambiguous identifier for an object. It is formatted as a series of numbers and periods that represent a hierarchy of information. Organizations such as HL7, Epic, and individual healthcare organizations have registered their own unique node in the OID namespace with the International Standards Organization (ISO). Some examples include:

Epic: 1.2.840.114350
NPI: 2.16.840.1.113883.4.6
HL7: 2.16.840.1.113883
OIDs are widely used by a variety of applications. FHIR APIs are only one place where you might see them. For example, HL7v2 messages, HL7v3 messages, and CDA exchanges all involve the use of OID identifiers. HL7 provides a useful site for reviewing existing registered OIDs: https://www.hl7.org/oid/.

Each organization is responsible for managing additional sub-nodes within their registered space. For example, Epic has registered OID 1.2.840.114350, and has assigned the following child OIDs (among many others):

1.2.840.114350.1.13.0.1.7.2.657380 – Represents the Interface Specification (AIP) master file in the open.epic sandbox environment
1.2.840.114350.1.13.0.1.7.5.737384.0 – Represents the Epic MRN ID type in the open.epic sandbox environment
1.2.840.114350.1.72.3.10 – Represents an observation about a patient FYI in Care Everywhere
Epic also issues child OIDs to each unique organization that uses Epic software, so that identifiers can be uniquely distinguished across organizations. When Epic issues a child OID to an organization, we have a specific structure we use. A common pattern is:

1.2.840.114350.1.13.<CID>.<EnvType>.7.<Value>

The pieces of this example OID represent the concepts outlined in the following table:

OID Segment

Meaning

1.2.840.114350

Epic’s root OID

.1

Indicates that this is an application-type ID

.13

The application ID. Some common application IDs include:

13: EDI
72: Care Everywhere
.<CID>

The unique Epic organization ID

.<EnvType>

The environment type. 1-Epic refers to Epic environments, such as the open.epic sandboxes. 2-Production and 3-Non-production refer to instances of Epic deployed at healthcare organizations.

1: Epic
2: Production
3: Non-production
.7

Indicates that this OID is intend for use in an HL7-type message

.<Value>

The value. This varies greatly depending on the concept we are generating an OID for. It might include multiple additional sub-nodes.

Note that the structure shown above is just one of several that Epic uses. It is included as an illustrative example. OIDs should be treated as opaque identifiers by external applications and systems. However, knowing this common structure can help analysts easily identify issues when troubleshooting.

Identifier Type
Epic uses this term differently than HL7. The distinction is important.

Within HL7 standards, an identifier type is a categorization of the identifier. For example, “MR” for medical record numbers or “DL” for driver’s license numbers. A given patient might have multiple identifiers with the same type (e.g., multiple medical record numbers).
Within Epic, identifier types are represented by Identity ID Type (IIT) records. IIT records store metadata about a specific set of identifiers. That metadata includes both the HL7 identifier type, (e.g., “MR”), which is stored in the “HL7 ID Type” field of the IIT record, as well as the HL7 identifier system, which is stored in the “HL7 Root” field of the IIT record. The identifier system is the globally unique namespace identifier for the set of identifiers. See the definition of identifier system below.
Examples
The following example in the HL7v2 message format demonstrates how HL7 identifiers are used:

Format: <ID>^^^<HL7 Assigning Authority>^<HL7 Identifier Type>
Example: 1234^^^Example Health System^MR
This example indicates that the identifier 1234 was assigned by Example Health System and is a Medical Record (MR) identifier. This example uses a human-readable “Example Health System” value for the assigning authority, but for integrations internal to an organization, often a short textual mnemonic like “EHSMRN” is used to communicate the assigning authority. However, for cross-organizational exchanges, an OID might be necessary because a short textual mnemonic might not be unique across organizations.

Here is a similar example in a FHIR format:

<identifier> 
    <use value="usual"/> 
    <type> 
        <coding> 
            <system value="http://terminology.hl7.org/CodeSystem/v2-0203"/> 
            <code value="MR"/> 
        </coding> 
    </type> 
    <system value="urn:oid:1.2.36.146.595.217.0.1"/> 
    <value value="1234"/> 
    <assigner> 
        <display value="Example Health System"/> 
    </assigner> 
</identifier>
Identifier System
From an HL7 perspective, you might have multiple identifiers with the same type (MR) but with different systems. If two organizations merge, their shared patient population might have two medical record numbers. Both of those identifiers are MR-type identifiers, but they are from different identifier systems. Identifier systems are important because, without qualifying an identifier with an identifier system, you cannot uniquely identify a patient. Ignoring identifier systems can lead to matching to the wrong patient, which can have patient safety implications.

In Epic, the HL7 identifier system is stored in the “HL7 Root” field of the ID Type record. In some cases, if this value is not specified in the IIT record, Epic falls back to using an auto-generated OID that is specific to the current environment. While this value may often follow the structure under Epic's root OID as noted in the table above, healthcare organizations may also register for their own nodes and populate this field on a given ID type with that value.

The meaning of the “HL7 Root” field

HL7 version 3 defined two methods of ensuring identifiers were globally unique: Universally Unique Identifiers (UUIDs), and Object Identifiers (OIDs). Epic software uses the OID method. To communicate unique identifiers, HL7v3 defined an “instance identifier” data type, which had two attributes: a root and an extension. The root attribute contained the root OID of the identifier system, and the extension attribute contained the identifier. 

When Epic first developed the ability to store an OID for the identifier system, we created the “HL7 Root” field in Epic IIT records. This was initially created to support HL7 version 3, and the item was named according to the HL7v3 terms, but the use of that item has since evolved to be used by Care Everywhere, HL7v2 and FHIR. 

In many integrations, Epic will look first to the “HL7 Root” field for the OID, but if this field is blank, we fall back to an auto-generated OID that is specific to the environment. The auto-generated OID includes a sub-node that indicates the environment type (PRD vs. non-PRD). It also includes a sub-node that identifies the specific healthcare organization. This often works well, as most IIT records are used to represent identifiers generated by that organization. However, this approach won’t work if the IIT record is used to store identifiers you receive from an external organization.

Organization-Specific IDs and Value Sets
FHIR APIs can sometimes require organization-specific identifiers or value sets. In these cases, developers and Epic organizations need to work together to coordinate usage of those identifiers or value sets.

FHIR APIs that use Epic-specific values such as Observation.Create (Vitals) use organization-specific OIDs. FHIR APIs that use standard value sets such as AllergyIntolerance.Search use either an OID or an industry URL as the coding system. For FHIR Create operations, you will need to use the OID or URL format, and the IDs will differ from the identifiers used by non-FHIR Epic APIs such as AddAllergy.
When an API returns data, it often returns multiple IDs that reference the same entity, such as a diagnosis or procedure. Each returned ID uses a different coding system. Therefore, you might be able to retrieve the ICD-10 or industry standard codes when an API returns a particular entity. For example, calling the Condition.Search FHIR API for a patient with hypertension returns both the ICD-10 code and an Epic ID for hypertension.

FHIR APIs typically use shared value sets that are linked in the “system” element, and represent well-defined HL7 standards.

The ValueSet.$expand API can in some cases help determine systems and codes supported by a resource. Epic currently supports ValueSet.$expand for the DocumentReference resource. Additional resources might be supported in future Epic versions.

We use cookies to improve our website. By accepting, you will receive these cookies from Epic on FHIR. Decline if you wish to 

OAuth 2.0 Errors
There are two types of OAuth 2.0 apps, launched apps and backend apps. Backend apps interact with only Epic's /token endpoint, while launched apps interact with the /token AND /authorize endpoints. We've broken out the error messages below by endpoint:

Authorize Endpoint
"Something went wrong trying to authorize the client. Please try logging in again."

Check that that redirect URI in your request matches one of the redirect URIs registered on the app. This includes the following:
If you've edited your app's URIs, wait for the client sync before testing
URIs are case sensitive
URIs must be exact matches. For instance "/" will not match "/index.html", even though browsers treat them the same
Check that the client ID in the request matches the client ID of the app, and that the response_type is code.
If you have a backend app encountering this error code, make sure the URL you're hitting ends in "/token" instead of "/authorize".
Make sure you're including a proper "aud" parameter in the request.
If using a POST request, make sure your body is of Content-Type: application/x-www-form-urlencoded instead of application/json, and make sure your request data is in the body instead of the query string (vice versa for GET requests).
"invalid_launch_token"

The client ID in the FDI must match the client ID of the app. Confirm the client ID in the app on Epic on FHIR make sure the client record exists in the Epic Community Member's Epic instance and that they have used that client ID in the integration. Make sure your app record and the authorization code in your request match exactly.
If you are redeeming a launch token at the wrong Epic instance (example: production vs non-production) this can occur.
404 or 500 error

Request URL might be too long. Shorten your state parameter.
I'm being asked to log in, but I'm launching from Epic/the Hyperspace Simulator

If you're launching from Epic (EHR launch) and still being asked to log in, have the app request the "launch" scope.
Token Endpoint
400 error:

"invalid_request" - Formatting of the HTTP Request can cause this issue. Try out the following:
Use the POST verb, not GET
Content-Type should be "application/x-www-form-urlencoded".
Do not send JSON, for example.
Content should be in the body of the request, not the querystring
There should be no "?" after "/token"
"invalid_client" - Your client authentication may be invalid. Try the following:
For apps using JWT authentication, refer to the linked JWT Auth Troubleshooting resource below.
If you're still having issues, try re-uploading your client authentication (client secret or public key) and waiting for the sync.
400 error: "unauthorized_client"

If using a Backend OAuth 2.0 integration, there is required community member setup that will cause this error if not completed. This step is auto-completed when testing in the FHIR sandbox.
API Call Errors
This section assumes your app has obtained an access token and is having issues making API calls using it. If you have not received an access token yet, refer to the OAuth 2.0 errors section above.

401 errors

400 usually means you had the right security, but the data in your request was incorrect somehow.
Check that you're putting data in the right place (body vs querystring).
Look for error messages in the response body to assist. Here is a common one:
NO-PATIENT-FOUND - When searching using an ID such as MRN, the ID Type in Epic needs to have a descriptor. Make sure the descriptor (I IIT 600) is populated for the target ID Type, and distribute to the app for searching.
It's helpful if your app is able to log the response body, since Epic returns detailed error messages for most APIs.
403 errors

For these errors, Epic identified who the client and user were, but denied access.
If the issue is with the client, we generally don't return a response body, just 403 Forbidden
In this case, check the API you are calling is attached to your client ID. Wait for the client to sync before testing any changes
For scope errors, the WWW-Authenticate HTTP Response header should say this:
Bearer error="insufficient_scope", error_description="The access token provided is valid, but is not authorized for this service"
If the issue is with the user, we generally return an error message describing why, such as:
"The authenticated user is not authorized to view the requested data" is common for FHIR calls. In this case, try the following:
Make sure you are handling access tokens correctly. If you mistakenly use one person's access token on another person's behalf, you'll see this error.
Organizations set up user security checks that also apply to access tokens. These security checks, if failed, produce this error.
If using a backend services app, these security checks are applied to the background user configured for your client ID. Otherwise, they are applied to the user who authenticated into your app.
Hyperspace/MyChart Embedding Errors
Many EHR Launched apps attempt to embed in Epic workflows, and rely on Epic build to do so. Below are common issues you might see when configuring one of these launches.

Attempted to embed in Hyperspace, but the window popped out to a new browser:

Check the FDI record has the correct launch type.
There are 2 types of FDIs and 2 types of launch activities, they need to match to respect launch settings:
PACS FDIs - Need RIS_PACS_REDIRECTOR
Web FDIs - Need MR_CLINKB_* (Active Guidelines)
Hyperspace launch displays a green/white spinning circle indefinitely (AGL spinner).

Confirm that all domains in the login workflow are added to the Epic Browser Allowlist.
Confirm that the workspace build points at the right FDI. Consider Active Guidelines debug mode to troubleshoot (shows URL navigated to).
App launches externally in MyChart mobile when launchtype specifies embedded launch.

Confirm that all the app domains are allowlisted in the MyChart Mobile FDI record.
Web Page Errors
OAuth involves several web servers taking control of a browser in a sequence/handshake. The following errors could come from EITHER the Interconnect/Authorization server or the third-party app's server when they are trying to display HTML.

This content cannot be displayed in a frame.

This could be hiding an OAuth 2.0 error, or an accidental login page.
Interconnect cannot be iframed, and is trying to show an error page or login page.
Will appear in trace logs, OR you can pop out the launch with FDI settings for "external window" workspace type.
Refer to these sections above for scenarios where Interconnect returns HTML:
"Something went wrong trying to authorize the client. Please try logging in again."
"I'm being asked to login, but I'm launching from Epic"
Otherwise, the third-party app is likely blocking the iframe.
The app needs to adjust the X-Frame-Options response header. The website can omit the "X-Frame-Options” header or set it to "ALLOW-FROM https://domain”. The domain should be that of the Hyperspace web server for the organization.
Content was blocked because it was not signed by a valid security certificate.

Accompanied by pink background
Implies a web site's certificate is invalid
Check the third-party server and Interconnect server for expired or invalid certificates.
This page can't be displayed

Error normally calls out the domain/server being requested
One cause is the browser being unable to resolve the website's IP address. Make sure the website's domain is publicly available, or at least available from the Hyperspace server for provider-facing embedded launches
If you can resolve the IP address, another cause is the server/website hanging up during the TLS handshake. Try using SSL Labs to diagnose why the server is hanging up. "Handshake Simulation" is especially useful since it calls out compatability with IE-11 and various windows versions
We use cookies to improve our website. By accepting, you will receive these cookies from Epic on FHIR. Decline if you wish to use Epic on FHIR without these cookies. Read our privacy policy here.


Frequently Asked Questions (FAQs) Contact Terms of Use Privacy Policy