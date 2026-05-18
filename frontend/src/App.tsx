import { BrowserRouter, Route, Routes } from "react-router-dom";

import AssetsPage from "./pages/AssetsPage";
import AssetDetailPage from "./pages/AssetDetailPage";
import CreateAssetPage from "./pages/CreateAssetPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AssetsPage />} />
        <Route path="/assets/:id" element={<AssetDetailPage />} />
        <Route path="/assets/create" element={<CreateAssetPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
