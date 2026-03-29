const dotenv = require('dotenv')
const { Pool } = require('pg')
const { createApp } = require('./app')

dotenv.config()

const PORT = Number(process.env.PORT || 5050)
const DATABASE_URL = process.env.DATABASE_URL || 'postgresql://novacura:novacura123@localhost:5432/novacura'

if (!process.env.AUTH_JWT_SECRET) {
  console.error('AUTH_JWT_SECRET is required. Set it in your environment before starting the server.')
  process.exit(1)
}

const pool = new Pool({
  connectionString: DATABASE_URL,
})

async function ensureSchema() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS nexus_contacts (
      id SERIAL PRIMARY KEY,
      name VARCHAR(140) NOT NULL,
      email VARCHAR(180) NOT NULL,
      company VARCHAR(180) NOT NULL,
      message TEXT NOT NULL,
      unsubscribe_token VARCHAR(96),
      unsubscribed_at TIMESTAMP WITH TIME ZONE,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    )
  `)

  await pool.query('ALTER TABLE nexus_contacts ADD COLUMN IF NOT EXISTS unsubscribe_token VARCHAR(96)')
  await pool.query('ALTER TABLE nexus_contacts ADD COLUMN IF NOT EXISTS unsubscribed_at TIMESTAMP WITH TIME ZONE')
  await pool.query(
    'CREATE UNIQUE INDEX IF NOT EXISTS nexus_contacts_unsubscribe_token_idx ON nexus_contacts(unsubscribe_token) WHERE unsubscribe_token IS NOT NULL'
  )

  await pool.query(`
    CREATE TABLE IF NOT EXISTS app_users (
      id SERIAL PRIMARY KEY,
      name VARCHAR(140) NOT NULL,
      email VARCHAR(180) UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    )
  `)
}

async function startServer() {
  let dbAvailable = true
  try {
    await ensureSchema()
  } catch (error) {
    dbAvailable = false
    console.error('Schema bootstrap failed, continuing without contact persistence:', error)
  }

  const app = createApp({
    query: pool.query.bind(pool),
    dbAvailable,
    requireJwtSecret: true,
  })

  app.listen(PORT, () => {
    const mode = dbAvailable ? 'DB available' : 'DB unavailable mode'
    console.log(`Pharma Nexus Node backend listening on ${PORT} (${mode})`)
  })
}

startServer().catch((error) => {
  console.error('Failed to start server:', error)
  process.exit(1)
})
