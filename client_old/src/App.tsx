import "@patternfly/react-core/dist/styles/base.css";
import { BrowserRouter, Routes, Route } from "react-router";
import type { ReactElement } from "react";

import AuthPage from "./pages/AuthPage";
import SignUpPage from "./pages/SignUpPage";
import AppLayout from "./layout/AppLayout";
import LogoutPage from "./pages/LogoutPage";

export default function App(): ReactElement {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/login" element={<AuthPage />} />
                <Route path="/signup" element={<SignUpPage />} />
                <Route path="/logout" element={<LogoutPage />} />
                <Route path="*" element={<AppLayout />} />
            </Routes>
        </BrowserRouter>
    );
}
