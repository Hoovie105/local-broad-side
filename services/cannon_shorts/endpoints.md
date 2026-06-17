# Endpoints

OpenAPI-style documentation for the YouTube Shorts microservice.

## OpenAPI Specification

```yaml
openapi: 3.0.3
info:
  title: Boardside — YouTube Shorts MS
  version: 0.1.0
  description: Processes YouTube Shorts uploads and reports results back to Core.
servers:
  - url: /
    description: Local or relative deployment
tags:
  - name: Health
  - name: Publish

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

  /publish:
    post:
      tags: [Publish]
      summary: Accept a standardized publish payload for YouTube Shorts
      operationId: publish
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/PublishPayload"
      responses:
        "202":
          description: Publish job accepted for background processing
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/PublishAcceptedResponse"
        "422":
          description: Validation error
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ValidationErrorResponse"

components:
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
          example: youtube-shorts

    PublishAcceptedResponse:
      type: object
      required: [accepted, job_id]
      properties:
        accepted:
          type: boolean
          example: true
        job_id:
          type: string
          example: 550e8400-e29b-41d4-a716-446655440000

    PublishPayload:
      type: object
      required:
        - job_id
        - video_url
        - caption
        - video_meta
        - platform_credentials
        - callback_url
      properties:
        job_id:
          type: string
        video_url:
          type: string
          format: uri
        caption:
          type: string
        video_meta:
          $ref: "#/components/schemas/VideoMeta"
        platform_credentials:
          type: object
          description: Platform-specific credentials forwarded by Core
          additionalProperties: true
        callback_url:
          type: string
          format: uri

    VideoMeta:
      type: object
      required:
        - duration_seconds
        - width
        - height
        - size_bytes
        - codec
        - format
      properties:
        duration_seconds:
          type: number
        width:
          type: integer
        height:
          type: integer
        size_bytes:
          type: integer
        codec:
          type: string
        format:
          type: string

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

- `POST /publish` accepts the shared `PublishPayload` contract from Core.
- The service always returns `202 Accepted` and finishes work in the background.
- Results are reported back to Core via the payload `callback_url`.
- This service only exposes `/health` and `/publish`.
