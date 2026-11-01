import React from 'react';
import {createRoot} from 'react-dom/client';
import App from './App';
import './styles.css';
import './support.css';
import {CustomerSupport} from './SupportChat';
createRoot(document.getElementById('root')!).render(<React.StrictMode>{window.location.pathname.replace(/\/$/,'') === '/support' ? <CustomerSupport/> : <App/>}</React.StrictMode>);
