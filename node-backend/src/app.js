const express = require('express')
const cors = require('cors')
const jwt = require('jsonwebtoken')
const bcrypt = require('bcryptjs')
const crypto = require('crypto')
const { OAuth2Client } = require('google-auth-library')
const { createContactEmailService } = require('./emailService')

function createApp({ query, dbAvailable = true, requireJwtSecret = false, contactEmailer }) {
  const app = express()
  const resolvedContactEmailer = contactEmailer || createContactEmailService()
  const googleClientId = process.env.GOOGLE_CLIENT_ID
  const googleClient = googleClientId ? new OAuth2Client(googleClientId) : null
  const jwtSecret = process.env.AUTH_JWT_SECRET
  if (requireJwtSecret && !jwtSecret) {
    throw new Error('AUTH_JWT_SECRET is required to start the backend')
  }
  const jwtAlgorithm = 'HS256'
  const inMemoryUsers = new Map()
  const inMemoryContacts = new Map()

  function issueSessionToken(user) {
    return jwt.sign(
      {
        sub: user.email,
        email: user.email,
        name: user.name,
        role: 'admin',
      },
      jwtSecret,
      { algorithm: jwtAlgorithm, expiresIn: '8h' }
    )
  }

  function renderUnsubscribeHtml({ title, message, statusCode }) {
    const headingColor = statusCode >= 400 ? '#7a1f1f' : '#18436f'
    return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>${title}</title>
</head>
<body style="margin:0;background:#f4f8fc;font-family:Verdana,Segoe UI,Arial,sans-serif;color:#11263d;">
  <div style="max-width:620px;margin:40px auto;padding:0 16px;">
    <div style="background:#ffffff;border:1px solid #d8e5f2;border-radius:14px;overflow:hidden;">
      <div style="padding:18px 22px;background:linear-gradient(120deg,#0f4c81,#1d7bd8);color:#ffffff;">PharmaNexus</div>
      <div style="padding:22px;">
        <h1 style="margin:0 0 12px 0;color:${headingColor};font-size:22px;">${title}</h1>
        <p style="margin:0;font-size:15px;line-height:1.6;">${message}</p>
      </div>
    </div>
  </div>
</body>
</html>`
  }

  app.use(cors())
  app.use(express.json())

  app.get('/health', (_req, res) => {
    res.json({ ok: true, service: 'pharma-nexus-node-backend' })
  })

  app.get('/api/strategies', (_req, res) => {
    res.json({
      options: [
        {
          id: 'basic',
          name: 'Traditional Pharma',
          summary: 'Optimize incumbent workflows with measured digital augmentation.',
          timeline: '5-year roadmap',
          focus: 'Operational stability and capital discipline',
        },
        {
          id: 'standard',
          name: 'Hybrid Approach',
          summary: 'Balance AI acceleration with validated stage-gate controls across R&D and commercialization.',
          timeline: '3-5 year roadmap',
          focus: 'Risk-adjusted growth and translational speed',
        },
        {
          id: 'premium',
          name: 'AI-First',
          summary: 'Re-architect the discovery pipeline around platform AI, adaptive trials, and model-driven prioritization.',
          timeline: '3-year roadmap',
          focus: 'Maximum innovation velocity and portfolio optionality',
        },
      ],
    })
  })

  app.post('/api/analysis', (req, res) => {
    const { mode = 'ai-vs-traditional' } = req.body || {}

    if (mode !== 'ai-vs-traditional') {
      return res.status(400).json({ error: 'Unsupported analysis mode.' })
    }

    return res.json({
      betterOption: 'Hybrid Approach',
      rationale:
        'The hybrid path captures most AI speed gains while preserving regulatory confidence and execution continuity.',
      riskNote:
        'Primary risk is data governance maturity; establish a 2-quarter quality and validation runway before scale-out.',
    })
  })

  app.post('/api/contact', async (req, res) => {
    const { name, email, company, message } = req.body || {}

    if (!name || !email || !company || !message) {
      return res.status(400).json({ success: false, message: 'All fields are required.' })
    }

    try {
      const unsubscribeToken = crypto.randomBytes(24).toString('hex')
      if (dbAvailable) {
        await query('INSERT INTO nexus_contacts (name, email, company, message, unsubscribe_token, unsubscribed_at) VALUES ($1, $2, $3, $4, $5, NULL)', [
          name,
          email,
          company,
          message,
          unsubscribeToken,
        ])
      } else {
        inMemoryContacts.set(unsubscribeToken, {
          name,
          email,
          company,
          message,
          createdAt: new Date().toISOString(),
          unsubscribedAt: null,
        })
      }

      let emailStatus = 'skipped'
      if (resolvedContactEmailer && typeof resolvedContactEmailer.sendContactEmails === 'function') {
        try {
          const unsubscribeUrl = `${req.protocol}://${req.get('host')}/api/unsubscribe?token=${encodeURIComponent(unsubscribeToken)}`
          const emailResult = await resolvedContactEmailer.sendContactEmails({
            name,
            email,
            company,
            message,
            unsubscribeUrl,
          })
          emailStatus = emailResult && emailResult.sent ? 'sent' : 'skipped'
        } catch (emailError) {
          emailStatus = 'failed'
          console.error('Contact email delivery failed:', emailError)
        }
      }

      return res.status(201).json({
        success: true,
        message: 'Thanks. Our strategy team will reach out shortly.',
        emailStatus,
        persistence: dbAvailable ? 'database' : 'memory',
      })
    } catch (error) {
      console.error('Contact insert failed:', error)
      return res.status(500).json({ success: false, message: 'Unable to store your request at this time.' })
    }
  })

  app.get('/api/unsubscribe', async (req, res) => {
    const token = String(req.query.token || '').trim()
    if (!token) {
      const html = renderUnsubscribeHtml({
        title: 'Missing token',
        message: 'Your unsubscribe link is missing a token. Please use the original link from your email.',
        statusCode: 400,
      })
      return res.status(400).type('html').send(html)
    }

    try {
      let found = false
      if (dbAvailable) {
        const result = await query(
          'UPDATE nexus_contacts SET unsubscribed_at = COALESCE(unsubscribed_at, CURRENT_TIMESTAMP) WHERE unsubscribe_token = $1 RETURNING id',
          [token]
        )
        found = result.rows.length > 0
      } else {
        const contact = inMemoryContacts.get(token)
        if (contact) {
          if (!contact.unsubscribedAt) {
            contact.unsubscribedAt = new Date().toISOString()
          }
          found = true
        }
      }

      if (!found) {
        const html = renderUnsubscribeHtml({
          title: 'Link invalid',
          message: 'This unsubscribe link is invalid or already expired.',
          statusCode: 404,
        })
        return res.status(404).type('html').send(html)
      }

      const html = renderUnsubscribeHtml({
        title: 'You are unsubscribed',
        message: 'You have been removed from future newsletter emails. You can subscribe again anytime from our site.',
        statusCode: 200,
      })
      return res.status(200).type('html').send(html)
    } catch (error) {
      console.error('Unsubscribe failed:', error)
      const html = renderUnsubscribeHtml({
        title: 'Unsubscribe failed',
        message: 'We were unable to process your request. Please try again later.',
        statusCode: 500,
      })
      return res.status(500).type('html').send(html)
    }
  })

  app.post('/api/auth/login', async (req, res) => {
    const { idToken } = req.body || {}

    // Google OAuth flow
    if (!idToken) {
      return res.status(400).json({ error: 'ID token is required.' })
    }

    if (!googleClient) {
      return res.status(500).json({ error: 'Google OAuth not configured.' })
    }

    try {
      const ticket = await googleClient.verifyIdToken({
        idToken: idToken,
        audience: googleClientId,
      })
      const payload = ticket.getPayload()

      const token = issueSessionToken({ email: payload.email, name: payload.name })

      return res.json({
        token,
        user: {
          email: payload.email,
          name: payload.name,
          picture: payload.picture
        },
      })
    } catch (error) {
      console.error('Google token verification failed:', error)
      return res.status(401).json({ error: 'Invalid or expired token.' })
    }
  })

  app.post('/api/auth/register', async (req, res) => {
    const { name, email, password } = req.body || {}

    if (!name || !email || !password) {
      return res.status(400).json({ error: 'Name, email, and password are required.' })
    }

    const normalizedEmail = String(email).trim().toLowerCase()
    if (!normalizedEmail.includes('@')) {
      return res.status(400).json({ error: 'Please enter a valid email address.' })
    }

    if (String(password).length < 8) {
      return res.status(400).json({ error: 'Password must be at least 8 characters long.' })
    }

    if (!jwtSecret) {
      return res.status(500).json({ error: 'JWT secret is not configured.' })
    }

    try {
      const passwordHash = await bcrypt.hash(String(password), 12)

      if (!dbAvailable) {
        if (inMemoryUsers.has(normalizedEmail)) {
          return res.status(409).json({ error: 'An account with this email already exists.' })
        }

        const user = { email: normalizedEmail, name: String(name).trim(), password_hash: passwordHash }
        inMemoryUsers.set(normalizedEmail, user)
        const token = issueSessionToken(user)
        return res.status(201).json({ token, user: { email: user.email, name: user.name } })
      }

      const created = await query(
        'INSERT INTO app_users (name, email, password_hash) VALUES ($1, $2, $3) RETURNING email, name',
        [String(name).trim(), normalizedEmail, passwordHash]
      )

      const user = created.rows[0]
      const token = issueSessionToken(user)
      return res.status(201).json({ token, user })
    } catch (error) {
      if (error && error.code === '23505') {
        return res.status(409).json({ error: 'An account with this email already exists.' })
      }
      console.error('Account registration failed:', error)
      return res.status(500).json({ error: 'Unable to create account right now.' })
    }
  })

  app.post('/api/auth/email-login', async (req, res) => {
    const { email, password } = req.body || {}

    if (!email || !password) {
      return res.status(400).json({ error: 'Email and password are required.' })
    }

    if (!jwtSecret) {
      return res.status(500).json({ error: 'JWT secret is not configured.' })
    }

    try {
      const normalizedEmail = String(email).trim().toLowerCase()

      if (!dbAvailable) {
        const user = inMemoryUsers.get(normalizedEmail)
        if (!user) {
          return res.status(401).json({ error: 'Invalid email or password.' })
        }

        const ok = await bcrypt.compare(String(password), user.password_hash)
        if (!ok) {
          return res.status(401).json({ error: 'Invalid email or password.' })
        }

        const token = issueSessionToken({ email: user.email, name: user.name })
        return res.json({ token, user: { email: user.email, name: user.name } })
      }

      const result = await query(
        'SELECT email, name, password_hash FROM app_users WHERE email = $1 LIMIT 1',
        [normalizedEmail]
      )

      if (!result.rows.length) {
        return res.status(401).json({ error: 'Invalid email or password.' })
      }

      const user = result.rows[0]
      const ok = await bcrypt.compare(String(password), user.password_hash)
      if (!ok) {
        return res.status(401).json({ error: 'Invalid email or password.' })
      }

      const token = issueSessionToken({ email: user.email, name: user.name })
      return res.json({ token, user: { email: user.email, name: user.name } })
    } catch (error) {
      console.error('Email login failed:', error)
      return res.status(500).json({ error: 'Unable to sign in right now.' })
    }
  })

  app.get('/api/auth/verify', (req, res) => {
    if (!jwtSecret) {
      return res.status(500).json({ error: 'JWT secret is not configured.' })
    }

    const authHeader = req.headers.authorization || ''
    if (!authHeader.startsWith('Bearer ')) {
      return res.status(401).json({ error: 'Authorization token required.' })
    }

    const token = authHeader.slice(7).trim()
    try {
      const payload = jwt.verify(token, jwtSecret, { algorithms: [jwtAlgorithm] })
      return res.json({ valid: true, user: { email: payload.email || payload.sub } })
    } catch (_error) {
      return res.status(401).json({ error: 'Invalid or expired token.' })
    }
  })

  app.get('/api/auth/me', (req, res) => {
    if (!jwtSecret) {
      return res.status(500).json({ error: 'JWT secret is not configured.' })
    }

    const authHeader = req.headers.authorization || ''
    if (!authHeader.startsWith('Bearer ')) {
      return res.status(401).json({ error: 'Authorization token required.' })
    }

    const token = authHeader.slice(7).trim()
    try {
      const payload = jwt.verify(token, jwtSecret, { algorithms: [jwtAlgorithm] })
      return res.json({
        email: payload.email,
        name: payload.name,
        picture: payload.picture,
      })
    } catch (_error) {
      return res.status(401).json({ error: 'Invalid or expired token.' })
    }
  })

  app.post('/api/auth/logout', (req, res) => {
    return res.json({ message: 'Logged out successfully.' })
  })

  app.use((req, res) => {
    res.status(404).json({ error: 'Not found' })
  })

  app.use((err, req, res, next) => {
    console.error('Unhandled server error:', err)
    res.status(500).json({ error: 'Internal server error' })
  })

  return app
}

module.exports = { createApp }