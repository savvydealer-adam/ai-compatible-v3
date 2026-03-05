import { useState, FormEvent } from "react";
import { useLocation } from "wouter";
import { useAnalysis } from "../hooks/useAnalysis";
import ProgressOverlay from "../components/ProgressOverlay";
import { Search, Zap, Shield, BarChart3 } from "lucide-react";

export default function Home() {
  const [url, setUrl] = useState("");
  const [, navigate] = useLocation();
  const { isLoading, error, progress, analyze } = useAnalysis();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    try {
      let input = url.trim().replace(/\/+$/, "");
      if (!/^https?:\/\//i.test(input)) {
        input = `https://${input}`;
      }
      const id = await analyze(input);
      navigate(`/results/${id}`);
    } catch {
      // Error handled by hook
    }
  };

  return (
    <div className="max-w-3xl mx-auto">
      {/* Hero */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">
          Is Your Dealership <span className="text-primary">AI Ready?</span>
        </h1>
        <p className="text-lg text-muted-foreground max-w-xl mx-auto">
          Analyze your website's compatibility with AI crawlers, chatbots, and
          search agents. Get a score, detailed report, and actionable
          recommendations.
        </p>
      </div>

      {/* URL Input */}
      <form onSubmit={handleSubmit} className="mb-12">
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground w-5 h-5" />
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Enter your dealership website URL..."
              className="w-full pl-10 pr-4 py-3 border rounded-lg text-lg focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
              disabled={isLoading}
            />
          </div>
          <button
            type="submit"
            disabled={isLoading || !url.trim()}
            className="px-8 py-3 bg-primary text-primary-foreground rounded-lg text-lg font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
          >
            {isLoading ? "Analyzing..." : "Analyze"}
          </button>
        </div>
        {error && (
          <p className="mt-2 text-sm text-destructive">{error}</p>
        )}
      </form>

      {/* Progress overlay */}
      {isLoading && progress && <ProgressOverlay progress={progress} />}

      {/* Feature cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
        <div className="p-6 rounded-lg border bg-card">
          <Shield className="w-8 h-8 text-blue-500 mb-3" />
          <h3 className="font-semibold mb-2">Bot Access</h3>
          <p className="text-sm text-muted-foreground">
            Test 17 AI crawler user agents for access and robots.txt
            permissions.
          </p>
        </div>
        <div className="p-6 rounded-lg border bg-card">
          <BarChart3 className="w-8 h-8 text-purple-500 mb-3" />
          <h3 className="font-semibold mb-2">Structured Data</h3>
          <p className="text-sm text-muted-foreground">
            Validate JSON-LD schemas on homepage, inventory, and vehicle detail
            pages.
          </p>
        </div>
        <div className="p-6 rounded-lg border bg-card">
          <Zap className="w-8 h-8 text-green-500 mb-3" />
          <h3 className="font-semibold mb-2">Discoverability</h3>
          <p className="text-sm text-muted-foreground">
            Check sitemaps, meta tags, and Markdown for Agents support.
          </p>
        </div>
      </div>

      {/* FAQ */}
      <div className="mt-16">
        <h2 className="text-2xl font-bold mb-6 text-center">FAQ</h2>
        <div className="space-y-4">
          <FaqItem
            question="What does this tool test?"
            answer="We test your dealership website across 6 categories: site accessibility, structured data (JSON-LD schemas), discoverability (sitemaps, meta tags), AI bot access (robots.txt + live HTTP tests with 17 crawler user agents), content signals, and bonus features like FAQPage schema and Markdown for Agents."
          />
          <FaqItem
            question="Why don't you test for llms.txt?"
            answer="llms.txt is an emerging standard that lets websites provide AI-friendly summaries of their content. While it's a promising concept, adoption is still extremely low across the automotive industry. We'll add llms.txt testing once it gains meaningful traction. For now, our scoring focuses on signals that AI systems actively use today."
          />
          <FaqItem
            question="How is my score calculated?"
            answer="Your score is on a 100-point scale across 6 weighted categories: Blocking Prevention (20 pts), Structured Data (25 pts), Discoverability (25 pts), Bot Access (15 pts), Signals (10 pts), and Bonus Features (5 pts). Letter grades range from A+ (96+) to F (below 65)."
          />
        </div>
      </div>
    </div>
  );
}

function FaqItem({ question, answer }: { question: string; answer: string }) {
  return (
    <details className="group p-4 rounded-lg border bg-card">
      <summary className="font-medium cursor-pointer list-none flex items-center justify-between">
        {question}
        <span className="text-muted-foreground group-open:rotate-180 transition-transform">
          &#9662;
        </span>
      </summary>
      <p className="mt-3 text-sm text-muted-foreground leading-relaxed">{answer}</p>
    </details>
  );
}
