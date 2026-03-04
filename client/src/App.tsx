import { Switch, Route } from "wouter";
import Home from "./pages/Home";
import Results from "./pages/Results";

function App() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-white">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <a href="/" className="text-xl font-bold text-primary">
            AI Compatible
          </a>
          <span className="text-sm text-muted-foreground">v3.0</span>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-4 py-8">
        <Switch>
          <Route path="/" component={Home} />
          <Route path="/results/:id" component={Results} />
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
      </footer>
    </div>
  );
}

export default App;
