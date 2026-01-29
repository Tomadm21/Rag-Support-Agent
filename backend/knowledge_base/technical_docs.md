# Technical Documentation

## API Documentation

### Authentication

All API requests require authentication using an API key.

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://api.example.com/v1/tickets
```

### Getting Your API Key

1. Navigate to Settings > API
2. Click "Generate New API Key"
3. Copy and store securely (shown only once)
4. Use in Authorization header

### Rate Limits

- Starter: 100 requests/minute
- Professional: 1,000 requests/minute
- Enterprise: 10,000 requests/minute

Rate limit headers:
- `X-RateLimit-Limit`: Your rate limit
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Timestamp when limit resets

### Common API Errors

#### 401 Unauthorized
- Cause: Invalid or missing API key
- Solution: Check your API key and ensure it's in the Authorization header

#### 429 Too Many Requests
- Cause: Exceeded rate limit
- Solution: Implement exponential backoff, respect X-RateLimit headers

#### 500 Internal Server Error
- Cause: Server-side issue
- Solution: Check status.example.com for incidents, retry with exponential backoff

#### 503 Service Unavailable
- Cause: Temporary maintenance or overload
- Solution: Retry after 60 seconds, check status page

## Webhook Integration

### Setting Up Webhooks

1. Go to Settings > Webhooks
2. Click "Add Webhook"
3. Enter webhook URL (must be HTTPS)
4. Select events to subscribe to
5. Set webhook secret for signature verification

### Event Types

- `ticket.created` - New ticket created
- `ticket.updated` - Ticket status changed
- `ticket.resolved` - Ticket marked as resolved
- `response.sent` - Response sent to customer

### Webhook Payload

```json
{
  "event": "ticket.created",
  "timestamp": "2025-01-29T10:30:00Z",
  "data": {
    "ticket_id": "TCK-12345",
    "customer_email": "customer@example.com",
    "subject": "API Error",
    "priority": "high"
  }
}
```

### Verifying Webhook Signatures

```python
import hmac
import hashlib

def verify_signature(payload, signature, secret):
    computed = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed, signature)
```

## Common Issues & Solutions

### API Connection Issues

**Problem**: Connection timeout or refused
**Causes**:
- Firewall blocking outbound HTTPS
- DNS resolution issues
- Network connectivity problems

**Solutions**:
1. Test connection: `curl -I https://api.example.com`
2. Check firewall allows outbound to *.example.com
3. Verify DNS resolves correctly
4. Try from different network

### Slow API Response Times

**Problem**: Requests taking >5 seconds
**Causes**:
- Large page sizes in list endpoints
- Complex filter queries
- Database performance

**Solutions**:
1. Reduce page size to 25-50 items
2. Use pagination instead of fetching all
3. Add indexes on filtered fields
4. Cache frequently accessed data

### 422 Validation Errors

**Problem**: Request rejected with validation errors
**Causes**:
- Missing required fields
- Invalid field formats
- Field exceeds max length

**Solutions**:
1. Check API documentation for required fields
2. Validate email format: `user@domain.com`
3. Ensure text fields under limits
4. Use ISO 8601 for dates: `2025-01-29T10:30:00Z`

## SDK Usage

### Python SDK

```python
from support_client import Client

client = Client(api_key="YOUR_API_KEY")

# Create ticket
ticket = client.tickets.create(
    subject="Issue with login",
    description="Cannot access my account",
    priority="high"
)

# List tickets
tickets = client.tickets.list(
    status="open",
    limit=50
)

# Update ticket
client.tickets.update(
    ticket_id="TCK-12345",
    status="resolved"
)
```

### JavaScript SDK

```javascript
const SupportClient = require('@support/client');

const client = new SupportClient({
  apiKey: 'YOUR_API_KEY'
});

// Create ticket
const ticket = await client.tickets.create({
  subject: 'Issue with login',
  description: 'Cannot access my account',
  priority: 'high'
});

// List tickets
const tickets = await client.tickets.list({
  status: 'open',
  limit: 50
});
```

## Performance Optimization

### Best Practices

1. **Use Pagination**: Don't fetch all records at once
2. **Implement Caching**: Cache frequently accessed data
3. **Batch Requests**: Combine multiple updates into one
4. **Use Webhooks**: Instead of polling for changes
5. **Compress Requests**: Use gzip compression
6. **Connection Pooling**: Reuse HTTP connections

### Monitoring

Track these metrics:
- API response time (p50, p95, p99)
- Error rate by endpoint
- Rate limit usage
- Webhook delivery success rate

## Security Best Practices

1. **Never expose API keys** in client-side code
2. **Rotate API keys** every 90 days
3. **Use HTTPS only** for all API calls
4. **Validate webhook signatures** to prevent spoofing
5. **Implement rate limiting** on your side
6. **Log all API access** for audit trail
7. **Use least privilege** - create keys with minimal required permissions
