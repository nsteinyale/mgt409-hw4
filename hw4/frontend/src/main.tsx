import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import { AuthProvider } from './auth.tsx'
import { ChatControlProvider } from './chatControl.tsx'
import { ChatResultsProvider } from './chatResults.tsx'
import { PageContextProvider } from './pageContext.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ChatResultsProvider>
          <PageContextProvider>
            <ChatControlProvider>
              <App />
            </ChatControlProvider>
          </PageContextProvider>
        </ChatResultsProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
