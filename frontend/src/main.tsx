import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./App";
import { ApiAuthProvider } from "./context/ApiAuthContext";
import { I18nProvider } from "./i18n";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <BrowserRouter>
      <I18nProvider>
        <ApiAuthProvider>
          <App />
        </ApiAuthProvider>
      </I18nProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
