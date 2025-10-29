import { BrowserRouter, Routes, Route } from "react-router";
import LoginPage from "./pages/LoginPage";
import MainPage from "./pages/MainPage";
import type { ReactElement } from "react";

const App = (): ReactElement => {
    const isAuthenticated = true;

    return (
        <BrowserRouter>
            <Routes>
                <Route
                    path="*"
                    element={isAuthenticated ? <MainPage /> : <LoginPage />}
                />
                {/* other public routes */}
                <Route path="*" element={<div>404 Not Found</div>} />
            </Routes>
        </BrowserRouter>
    );
};

export default App;
