import { BrowserRouter, Routes, Route } from "react-router";
import MainPage from "./pages/MainPage";
import type { ReactElement } from "react";
import AuthPage from "./pages/AuthPage";
import SignUpPage from "./pages/SignUpPage";

const App = (): ReactElement => {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/login" element={<AuthPage />} />
                <Route path="/signup" element={<SignUpPage />} />
                <Route path="*" element={<MainPage />} />
            </Routes>
        </BrowserRouter>
    );
};

export default App;
