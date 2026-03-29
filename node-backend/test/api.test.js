const test = require('node:test')
const assert = require('node:assert/strict')
const jwt = require('jsonwebtoken')
const bcrypt = require('bcryptjs')
const { createApp } = require('../src/app')

function startTestServer(queryImpl, options = {}) {
  const app = createApp({ query: queryImpl, ...options })
  return new Promise((resolve) => {
    const server = app.listen(0, () => {
      const address = server.address()
      resolve({
        server,
        baseUrl: `http://127.0.0.1:${address.port}`,
      })
    })
  })
}

test('GET /api/strategies returns 3 options', async () => {
  const { server, baseUrl } = await startTestServer(async () => ({ rows: [] }))

  try {
    const res = await fetch(`${baseUrl}/api/strategies`)
    const body = await res.json()

    assert.equal(res.status, 200)
    assert.ok(Array.isArray(body.options))
    assert.equal(body.options.length, 3)
  } finally {
    server.close()
  }
})

test('POST /api/analysis validates mode and returns recommendation', async () => {
  const { server, baseUrl } = await startTestServer(async () => ({ rows: [] }))

  try {
    const okRes = await fetch(`${baseUrl}/api/analysis`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: 'ai-vs-traditional' }),
    })
    const okBody = await okRes.json()
    assert.equal(okRes.status, 200)
    assert.equal(okBody.betterOption, 'Hybrid Approach')

    const badRes = await fetch(`${baseUrl}/api/analysis`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: 'unsupported-mode' }),
    })
    assert.equal(badRes.status, 400)
  } finally {
    server.close()
  }
})

test('POST /api/contact returns 201 on success', async () => {
  let called = false
  let emailCalled = false
  let contactInsertParams = null
  const { server, baseUrl } = await startTestServer(async (_sql, params) => {
    called = true
    contactInsertParams = params
    return { rows: [] }
  }, {
    contactEmailer: {
      async sendContactEmails() {
        emailCalled = true
        return { sent: true, provider: 'test' }
      },
    },
  })

  try {
    const res = await fetch(`${baseUrl}/api/contact`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'Test User',
        email: 'test@example.com',
        company: 'NovaCura',
        message: 'Hello',
      }),
    })
    const body = await res.json()

    assert.equal(res.status, 201)
    assert.equal(body.success, true)
    assert.equal(called, true)
    assert.equal(emailCalled, true)
    assert.equal(body.emailStatus, 'sent')
    assert.equal(contactInsertParams.length, 5)
    assert.ok(typeof contactInsertParams[4] === 'string' && contactInsertParams[4].length >= 40)
  } finally {
    server.close()
  }
})

test('POST /api/contact still returns 201 when email delivery fails', async () => {
  const { server, baseUrl } = await startTestServer(async () => ({ rows: [] }), {
    contactEmailer: {
      async sendContactEmails() {
        throw new Error('email provider unavailable')
      },
    },
  })

  try {
    const res = await fetch(`${baseUrl}/api/contact`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'Test User',
        email: 'test@example.com',
        company: 'NovaCura',
        message: 'Hello',
      }),
    })
    const body = await res.json()

    assert.equal(res.status, 201)
    assert.equal(body.success, true)
    assert.equal(body.emailStatus, 'failed')
  } finally {
    server.close()
  }
})

test('POST /api/contact returns 400 when fields missing', async () => {
  const { server, baseUrl } = await startTestServer(async () => ({ rows: [] }))

  try {
    const res = await fetch(`${baseUrl}/api/contact`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: 'test@example.com' }),
    })

    assert.equal(res.status, 400)
  } finally {
    server.close()
  }
})

test('POST /api/contact returns 500 when query fails', async () => {
  const { server, baseUrl } = await startTestServer(async () => {
    throw new Error('db down')
  })

  try {
    const res = await fetch(`${baseUrl}/api/contact`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'Test User',
        email: 'test@example.com',
        company: 'NovaCura',
        message: 'Hello',
      }),
    })

    assert.equal(res.status, 500)
  } finally {
    server.close()
  }
})

test('GET /api/unsubscribe returns 400 when token is missing', async () => {
  const { server, baseUrl } = await startTestServer(async () => ({ rows: [] }))

  try {
    const res = await fetch(`${baseUrl}/api/unsubscribe`)
    const body = await res.text()

    assert.equal(res.status, 400)
    assert.ok(body.includes('Missing token'))
  } finally {
    server.close()
  }
})

test('GET /api/unsubscribe returns 404 when token does not exist', async () => {
  const { server, baseUrl } = await startTestServer(async () => ({ rows: [] }))

  try {
    const res = await fetch(`${baseUrl}/api/unsubscribe?token=does-not-exist`)
    const body = await res.text()

    assert.equal(res.status, 404)
    assert.ok(body.includes('Link invalid'))
  } finally {
    server.close()
  }
})

test('GET /api/unsubscribe returns 200 for a valid token', async () => {
  const { server, baseUrl } = await startTestServer(async () => ({ rows: [{ id: 1 }] }))

  try {
    const res = await fetch(`${baseUrl}/api/unsubscribe?token=valid-token`)
    const body = await res.text()

    assert.equal(res.status, 200)
    assert.ok(body.includes('You are unsubscribed'))
  } finally {
    server.close()
  }
})

test('POST /api/auth/login returns 400 when idToken missing', async () => {
  const { server, baseUrl } = await startTestServer(async () => ({ rows: [] }))

  try {
    const res = await fetch(`${baseUrl}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })

    assert.equal(res.status, 400)
  } finally {
    server.close()
  }
})

test('POST /api/auth/login returns 500 when Google OAuth is not configured', async () => {
  const { server, baseUrl } = await startTestServer(async () => ({ rows: [] }))

  try {
    const res = await fetch(`${baseUrl}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ idToken: 'fake-token' }),
    })

    assert.equal(res.status, 500)
  } finally {
    server.close()
  }
})

test('GET /api/auth/verify validates token', async () => {
  process.env.AUTH_JWT_SECRET = process.env.AUTH_JWT_SECRET || 'test-secret'
  const { server, baseUrl } = await startTestServer(async () => ({ rows: [] }))

  try {
    const token = jwt.sign(
      {
        sub: 'admin@pharmanexus.ai',
        email: 'admin@pharmanexus.ai',
        role: 'admin',
      },
      process.env.AUTH_JWT_SECRET,
      { algorithm: 'HS256', expiresIn: '8h' }
    )

    const verifyRes = await fetch(`${baseUrl}/api/auth/verify`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    const verifyBody = await verifyRes.json()

    assert.equal(verifyRes.status, 200)
    assert.equal(verifyBody.valid, true)
  } finally {
    server.close()
  }
})

test('POST /api/auth/register creates account and returns token', async () => {
  process.env.AUTH_JWT_SECRET = process.env.AUTH_JWT_SECRET || 'test-secret'
  let insertedParams = null
  const { server, baseUrl } = await startTestServer(async (_sql, params) => {
    insertedParams = params
    return {
      rows: [
        {
          email: params[1],
          name: params[0],
        },
      ],
    }
  })

  try {
    const res = await fetch(`${baseUrl}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'Test User',
        email: 'test@example.com',
        password: 'secure-pass-123',
      }),
    })
    const body = await res.json()

    assert.equal(res.status, 201)
    assert.equal(body.user.email, 'test@example.com')
    assert.ok(typeof body.token === 'string' && body.token.length > 10)
    assert.equal(insertedParams[0], 'Test User')
    assert.equal(insertedParams[1], 'test@example.com')
    assert.notEqual(insertedParams[2], 'secure-pass-123')
  } finally {
    server.close()
  }
})

test('POST /api/auth/email-login validates password and returns token', async () => {
  process.env.AUTH_JWT_SECRET = process.env.AUTH_JWT_SECRET || 'test-secret'
  const passwordHash = await bcrypt.hash('secure-pass-123', 10)
  const { server, baseUrl } = await startTestServer(async () => ({
    rows: [
      {
        email: 'test@example.com',
        name: 'Test User',
        password_hash: passwordHash,
      },
    ],
  }))

  try {
    const res = await fetch(`${baseUrl}/api/auth/email-login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: 'test@example.com',
        password: 'secure-pass-123',
      }),
    })
    const body = await res.json()

    assert.equal(res.status, 200)
    assert.equal(body.user.email, 'test@example.com')
    assert.ok(typeof body.token === 'string' && body.token.length > 10)
  } finally {
    server.close()
  }
})
