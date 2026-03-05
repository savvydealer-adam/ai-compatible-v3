import { GoogleOAuthProvider, GoogleLogin, type CredentialResponse } from "@react-oauth/google";
import { Switch, Route } from "wouter";
import { useAuth } from "./hooks/useAuth";
import { googleAuth } from "./lib/api";
import Admin from "./pages/Admin";
import Home from "./pages/Home";
import Results from "./pages/Results";
import { LogOut } from "lucide-react";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";

function App() {
  const auth = useAuth();

  const handleFooterLogin = async (response: CredentialResponse) => {
    if (!response.credential) return;
    try {
      const res = await googleAuth({
        credential: response.credential,
        dealership: "",
        phone: "",
      });
      if (res.jwt) auth.login(res.jwt);
    } catch {
      // Silent fail — user can retry
    }
  };

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
    <div className="min-h-screen bg-background">
      <header className="border-b bg-white">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <a href="/" className="text-xl font-bold text-primary">
            AI Compatible
          </a>
          {auth.isLoggedIn && auth.user ? (
            <div className="flex items-center gap-3">
              <span className="text-sm text-muted-foreground">
                {auth.user.name}{" "}
                <span className="hidden sm:inline">({auth.user.email})</span>
              </span>
              <button
                onClick={auth.logout}
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                <LogOut className="w-3 h-3" /> Sign Out
              </button>
            </div>
          ) : (
            <span className="text-sm text-muted-foreground">v3.0</span>
          )}
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-4 py-8">
        <Switch>
          <Route path="/" component={Home} />
          <Route path="/results/:id" component={Results} />
          <Route path="/admin" component={Admin} />
          <Route>
            <div className="text-center py-20">
              <h1 className="text-2xl font-bold">Page not found</h1>
              <a href="/" className="text-primary mt-4 inline-block">Go home</a>
            </div>
          </Route>
        </Switch>
      </main>
      <footer className="border-t mt-16 py-6 text-center text-sm text-muted-foreground">
        <p>AI Compatible v3 &mdash; Built by <a href="https://savvydealer.com" className="text-primary hover:underline">Savvy Dealer</a></p>
        {!auth.isLoggedIn && (
          <div className="mt-3 flex justify-center">
            <GoogleLogin
              onSuccess={handleFooterLogin}
              size="small"
              text="signin"
              shape="pill"
            />
          </div>
        )}
      </footer>
    </div>
    </GoogleOAuthProvider>
  );
}

export default App;
