import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider } from 'antd'
import { BrowserRouter } from 'react-router-dom'
import { GoogleOAuthProvider } from '@react-oauth/google'
import App from './App'
import { AuthProvider } from '@/contexts/AuthContext'
import './index.css'
import 'antd/dist/reset.css'

const googleClientId = (import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined) ?? ''
const googleOAuthConfigured = googleClientId.trim().length > 0 && !googleClientId.startsWith('your-google-client-id')

if (!googleOAuthConfigured) {
  console.warn('Google OAuth is disabled: set VITE_GOOGLE_CLIENT_ID in frontend/.env')
}

const appContent = (
  <ConfigProvider
    theme={{
      token: {
        colorPrimary: '#18A07D',
        colorInfo: '#4D8FFF',
        colorSuccess: '#18A07D',
        colorWarning: '#F59E0B',
        colorError: '#EF4444',
        borderRadius: 12,
        fontFamily: 'DM Sans, sans-serif',
      },
    }}
  >
    <AuthProvider>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </AuthProvider>
  </ConfigProvider>
)

const appTree = googleOAuthConfigured ? (
  <GoogleOAuthProvider clientId={googleClientId}>{appContent}</GoogleOAuthProvider>
) : (
  appContent
)

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    {appTree}
  </React.StrictMode>
)
