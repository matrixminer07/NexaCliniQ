function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function buildContactEmailContent({ name, email, company, message, unsubscribeUrl }) {
  const safeName = escapeHtml(name)
  const safeEmail = escapeHtml(email)
  const safeCompany = escapeHtml(company)
  const safeMessage = escapeHtml(message)
  const safeUnsubscribeUrl = escapeHtml(unsubscribeUrl || '')

  const brandName = escapeHtml(process.env.CONTACT_BRAND_NAME || 'PharmaNexus')
  const primaryColor = '#0f4c81'
  const accentColor = '#1d7bd8'
  const pageBg = '#f4f8fc'
  const cardBg = '#ffffff'

  const shellStart = `<div style="margin:0;padding:24px;background:${pageBg};font-family:Verdana,Segoe UI,Arial,sans-serif;color:#10243a;">`
  const cardStart = `<div style="max-width:620px;margin:0 auto;background:${cardBg};border:1px solid #d8e5f2;border-radius:16px;overflow:hidden;">`
  const hero = `<div style="padding:20px 24px;background:linear-gradient(120deg,${primaryColor},${accentColor});color:#ffffff;"><h1 style="margin:0;font-size:22px;line-height:1.25;">${brandName}</h1><p style="margin:6px 0 0 0;font-size:13px;opacity:0.92;">Biotech intelligence updates</p></div>`
  const cardEnd = '</div>'
  const shellEnd = '</div>'

  return {
    user: {
      subject: 'You are subscribed to PharmaNexus updates',
      text: `Hi ${name},\n\nThanks for subscribing to PharmaNexus updates.\n\nWe will share strategic biotech intelligence and market inflection points with you soon.\n\nTo unsubscribe at any time, use this link:\n${unsubscribeUrl || 'Unsubscribe link unavailable'}\n\n- PharmaNexus Team`,
      html:
        `${shellStart}${cardStart}${hero}` +
        `<div style="padding:24px;"><p style="margin:0 0 14px 0;font-size:15px;">Hi ${safeName},</p><p style="margin:0 0 14px 0;font-size:15px;line-height:1.6;">Thanks for subscribing to ${brandName} updates.</p><p style="margin:0 0 22px 0;font-size:15px;line-height:1.6;">We will share strategic biotech intelligence and market inflection points with you soon.</p><a href="${safeUnsubscribeUrl}" style="display:inline-block;padding:10px 16px;background:${primaryColor};color:#ffffff;text-decoration:none;border-radius:8px;font-size:14px;">Unsubscribe</a><p style="margin:16px 0 0 0;font-size:12px;color:#5a718a;">If the button does not work, copy this URL: ${safeUnsubscribeUrl}</p></div>${cardEnd}${shellEnd}`,
    },
    team: {
      subject: 'New newsletter subscription',
      text: `New subscription received.\n\nName: ${name}\nEmail: ${email}\nCompany: ${company}\nMessage: ${message}`,
      html:
        `${shellStart}${cardStart}${hero}` +
        `<div style="padding:24px;"><h3 style="margin:0 0 14px 0;font-size:18px;">New newsletter subscription</h3><p style="margin:0 0 8px 0;"><strong>Name:</strong> ${safeName}</p><p style="margin:0 0 8px 0;"><strong>Email:</strong> ${safeEmail}</p><p style="margin:0 0 8px 0;"><strong>Company:</strong> ${safeCompany}</p><p style="margin:0;"><strong>Message:</strong> ${safeMessage}</p></div>${cardEnd}${shellEnd}`,
    },
  }
}

async function sendViaResend({ apiKey, fromEmail, to, subject, text, html }) {
  const response = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      from: fromEmail,
      to: Array.isArray(to) ? to : [to],
      subject,
      text,
      html,
    }),
  })

  if (!response.ok) {
    const body = await response.text()
    throw new Error(`Resend send failed (${response.status}): ${body}`)
  }
}

async function sendViaSendGrid({ apiKey, fromEmail, to, subject, text, html, replyTo }) {
  const response = await fetch('https://api.sendgrid.com/v3/mail/send', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      personalizations: [{ to: (Array.isArray(to) ? to : [to]).map((email) => ({ email })) }],
      from: { email: fromEmail },
      reply_to: replyTo ? { email: replyTo } : undefined,
      subject,
      content: [
        { type: 'text/plain', value: text },
        { type: 'text/html', value: html },
      ],
    }),
  })

  if (!response.ok) {
    const body = await response.text()
    throw new Error(`SendGrid send failed (${response.status}): ${body}`)
  }
}

function createContactEmailService() {
  const resendApiKey = process.env.RESEND_API_KEY
  const sendgridApiKey = process.env.SENDGRID_API_KEY
  const fromEmail = process.env.CONTACT_FROM_EMAIL || process.env.RESEND_FROM_EMAIL || process.env.SENDGRID_FROM_EMAIL
  const teamEmail = process.env.CONTACT_TEAM_EMAIL
  const replyTo = process.env.CONTACT_REPLY_TO

  let provider = null
  if (resendApiKey) {
    provider = 'resend'
  } else if (sendgridApiKey) {
    provider = 'sendgrid'
  }

  const configured = Boolean(provider && fromEmail && teamEmail)

  return {
    configured,
    provider,
    async sendContactEmails(payload) {
      if (!configured) {
        return { sent: false, reason: 'email-provider-not-configured' }
      }

      const content = buildContactEmailContent(payload)
      const sender =
        provider === 'resend'
          ? (mail) => sendViaResend({ ...mail, apiKey: resendApiKey, fromEmail })
          : (mail) =>
              sendViaSendGrid({
                ...mail,
                apiKey: sendgridApiKey,
                fromEmail,
                replyTo,
              })

      await Promise.all([
        sender({
          to: payload.email,
          subject: content.user.subject,
          text: content.user.text,
          html: content.user.html,
        }),
        sender({
          to: teamEmail,
          subject: content.team.subject,
          text: content.team.text,
          html: content.team.html,
        }),
      ])

      return { sent: true, provider }
    },
  }
}

module.exports = { createContactEmailService }
