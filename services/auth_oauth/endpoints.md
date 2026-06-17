# Endpoints

OpenAPI-style documentation for Boardside Auth.

## OpenAPI Specification

```yaml
openapi: 3.0.3
info:
  title: Boardside — Auth Service
  version: 0.1.0
  description: User accounts, JWT sessions, and platform OAuth flows.
servers:
  - url: /
    description: Local or relative deployment
tags:
  - name: Health
  - name: Auth
  - name: OAuth
  - name: TikTok OAuth
  - name: YouTube OAuth
  - name: Internal

paths:
  /health:
    get:
      tags: [Health]
      summary: Health check
      operationId: health
      responses:
        "200":
          description: Service is healthy
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/HealthResponse"

  /auth/register:
    post:
      tags: [Auth]
      summary: Register a new user
      operationId: register
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/RegisterRequest"
      responses:
        "201":
          description: User created
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/UserResponse"
        "409":
          description: Email already registered
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"
        "422":
          description: Validation error
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ValidationErrorResponse"

  /auth/login:
    post:
      tags: [Auth]
      summary: Log in and receive a JWT
      operationId: login
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/LoginRequest"
      responses:
        "200":
          description: Token issued
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/TokenResponse"
        "401":
          description: Invalid credentials
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"
        "403":
          description: Account is disabled
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"
        "422":
          description: Validation error
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ValidationErrorResponse"

  /auth/logout:
    post:
      tags: [Auth]
      summary: Invalidate the current JWT
      operationId: logout
      security:
        - bearerAuth: []
      responses:
        "200":
          description: Token blacklisted
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/LogoutResponse"
        "401":
          description: Missing or invalid bearer token
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"

  /auth/instagram:
    get:
      tags: [OAuth]
      summary: Start Instagram OAuth flow
      operationId: connectInstagram
      parameters:
        - name: token
          in: query
          required: true
          schema:
            type: string
          description: User JWT to validate before starting OAuth
      responses:
        "307":
          description: Redirects user to Meta consent screen
        "401":
          description: Invalid or blacklisted token
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"

  /auth/instagram/callback:
    get:
      tags: [OAuth]
      summary: Handle Instagram OAuth callback
      operationId: instagramCallback
      parameters:
        - name: code
          in: query
          required: true
          schema:
            type: string
        - name: state
          in: query
          required: true
          schema:
            type: string
          description: User ID passed through the OAuth state parameter
        - name: error
          in: query
          required: false
          schema:
            type: string
          description: Error returned by Meta if the user denied consent
      responses:
        "307":
          description: Redirects back to frontend success or error page
        "400":
          description: Invalid state parameter
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"

  /auth/tiktok:
    get:
      tags: [TikTok OAuth]
      summary: Start TikTok OAuth flow
      operationId: connectTikTok
      parameters:
        - name: token
          in: query
          required: true
          schema:
            type: string
          description: User JWT to validate before starting OAuth
      responses:
        "307":
          description: Redirects user to TikTok consent screen
        "401":
          description: Invalid or blacklisted token
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"

  /auth/tiktok/callback:
    get:
      tags: [TikTok OAuth]
      summary: Handle TikTok OAuth callback
      operationId: tiktokCallback
      parameters:
        - name: code
          in: query
          required: false
          schema:
            type: string
        - name: state
          in: query
          required: true
          schema:
            type: string
          description: User ID passed through the OAuth state parameter
        - name: error
          in: query
          required: false
          schema:
            type: string
        - name: error_description
          in: query
          required: false
          schema:
            type: string
      responses:
        "307":
          description: Redirects back to frontend success or error page
        "400":
          description: Invalid state parameter or missing PKCE verifier
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"

  /auth/youtube:
    get:
      tags: [YouTube OAuth]
      summary: Start YouTube OAuth flow
      operationId: connectYouTube
      parameters:
        - name: token
          in: query
          required: true
          schema:
            type: string
          description: User JWT to validate before starting OAuth
      responses:
        "307":
          description: Redirects user to Google consent screen
        "401":
          description: Invalid or blacklisted token
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"

  /auth/youtube/callback:
    get:
      tags: [YouTube OAuth]
      summary: Handle YouTube OAuth callback
      operationId: youtubeCallback
      parameters:
        - name: code
          in: query
          required: false
          schema:
            type: string
        - name: state
          in: query
          required: true
          schema:
            type: string
          description: User ID passed through the OAuth state parameter
        - name: error
          in: query
          required: false
          schema:
            type: string
          description: Error returned by Google if the user denied consent
      responses:
        "307":
          description: Redirects back to frontend success or error page
        "400":
          description: Invalid state parameter
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"

  /auth/connections:
    get:
      tags: [OAuth]
      summary: List active platform connections for the current user
      operationId: getConnections
      security:
        - bearerAuth: []
      responses:
        "200":
          description: List of connected platforms
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ConnectionsResponse"
        "401":
          description: Missing or invalid bearer token
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"

  /internal/validate-token:
    post:
      tags: [Internal]
      summary: Validate a JWT and resolve the user ID
      operationId: validateToken
      security:
        - internalKey: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/ValidateTokenRequest"
      responses:
        "200":
          description: Token validation result
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ValidateTokenResponse"
        "403":
          description: Invalid internal API key
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"

  /internal/credentials/{user_id}/{platform}:
    get:
      tags: [Internal]
      summary: Get decrypted credentials for a user's platform connection
      operationId: getPlatformCredentials
      security:
        - internalKey: []
      parameters:
        - name: user_id
          in: path
          required: true
          schema:
            type: string
        - name: platform
          in: path
          required: true
          schema:
            type: string
          description: Platform name such as instagram, tiktok, or youtube
      responses:
        "200":
          description: Platform credentials returned
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/PlatformCredentialsResponse"
        "403":
          description: Invalid internal API key
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"
        "404":
          description: No active platform connection found
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
    internalKey:
      type: apiKey
      in: header
      name: X-Internal-Key

  schemas:
    HealthResponse:
      type: object
      required: [status, service]
      properties:
        status:
          type: string
          example: ok
        service:
          type: string
          example: auth

    RegisterRequest:
      type: object
      required: [email, password]
      properties:
        email:
          type: string
          format: email
        password:
          type: string

    LoginRequest:
      type: object
      required: [email, password]
      properties:
        email:
          type: string
          format: email
        password:
          type: string

    TokenResponse:
      type: object
      required: [access_token, token_type]
      properties:
        access_token:
          type: string
        token_type:
          type: string
          example: bearer

    UserResponse:
      type: object
      required: [id, email]
      properties:
        id:
          type: string
        email:
          type: string
          format: email

    LogoutResponse:
      type: object
      required: [message]
      properties:
        message:
          type: string
          example: Logged out successfully.

    ValidateTokenRequest:
      type: object
      required: [token]
      properties:
        token:
          type: string

    ValidateTokenResponse:
      type: object
      required: [valid]
      properties:
        valid:
          type: boolean
        user_id:
          type: string
          nullable: true

    PlatformCredentialsResponse:
      type: object
      required: [platform, access_token, platform_user_id]
      properties:
        platform:
          type: string
        access_token:
          type: string
        platform_user_id:
          type: string

    ConnectionsResponse:
      type: array
      items:
        type: object
        required: [platform]
        properties:
          platform:
            type: string
            example: instagram

    ErrorResponse:
      type: object
      required: [detail]
      properties:
        detail:
          oneOf:
            - type: string
            - type: object
            - type: array

    ValidationErrorResponse:
      type: object
      properties:
        detail:
          type: array
          items:
            type: object
            properties:
              loc:
                type: array
                items:
                  oneOf:
                    - type: string
                    - type: integer
              msg:
                type: string
              type:
                type: string
```

## Notes

- `GET /auth/instagram`, `GET /auth/tiktok`, and `GET /auth/youtube` return redirects, not JSON.
- The `/auth/*/callback` routes redirect back to the frontend on success or OAuth denial.
- `POST /internal/validate-token` and `GET /internal/credentials/{user_id}/{platform}` are internal-only and require `X-Internal-Key`.
- `GET /auth/connections` is the frontend-facing way to check active platform links.
