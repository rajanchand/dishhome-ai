import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { AuthProvider, useAuth } from "./lib/auth";
import Layout from "./components/Layout";
import ErrorBoundary from "./components/ErrorBoundary";
import { NetworkStatusBridge, ToastProvider } from "./components/Toast";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Calls from "./pages/Calls";
import CallDetail from "./pages/CallDetail";
import VoiceLab from "./pages/VoiceLab";
import Integrations from "./pages/Integrations";
import Settings from "./pages/Settings";
import Inbox from "./pages/Inbox";
import Customers from "./pages/Customers";
import Contacts from "./pages/Contacts";
import FAQs from "./pages/FAQs";
import Campaigns from "./pages/Campaigns";
import CampaignDetail from "./pages/CampaignDetail";
import SavedReplies from "./pages/SavedReplies";

function RequireAuth({ children }: { children: JSX.Element }) {
  const { user, loading } = useAuth();
  const loc = useLocation();
  if (loading)
    return (
      <div className="min-h-screen flex items-center justify-center text-dishhome-ink/50">
        Loading…
      </div>
    );
  if (!user)
    return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  return children;
}

export default function App() {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <NetworkStatusBridge />
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route
                element={
                  <RequireAuth>
                    <Layout />
                  </RequireAuth>
                }
              >
                <Route index element={<Dashboard />} />
                <Route path="calls" element={<Calls />} />
                <Route path="calls/:id" element={<CallDetail />} />
                <Route path="inbox" element={<Inbox />} />
                <Route path="customers" element={<Customers />} />
                <Route path="contacts" element={<Contacts />} />
                <Route path="faqs" element={<FAQs />} />
                <Route path="campaigns" element={<Campaigns />} />
                <Route path="campaigns/:id" element={<CampaignDetail />} />
                <Route path="saved-replies" element={<SavedReplies />} />
                <Route path="voice" element={<VoiceLab />} />
                <Route path="integrations" element={<Integrations />} />
                <Route path="settings" element={<Settings />} />
              </Route>
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </ToastProvider>
    </ErrorBoundary>
  );
}
