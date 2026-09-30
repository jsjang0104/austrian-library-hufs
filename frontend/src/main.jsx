import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import './global.css';
import App from './App.jsx';
import { migrateLegacyHashRoute } from './legacyRoutes';
import { AuthProvider } from './AuthContext'; 

migrateLegacyHashRoute();

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </AuthProvider>
  </StrictMode>,
);