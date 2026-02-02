import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Shell } from "../../components/Shell";

const client = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={client}>
      {children}
    </QueryClientProvider>
  );
}

describe("Shell", () => {
  it("renders children", () => {
    render(
      <Wrapper>
        <Shell>
          <span data-testid="child">Content</span>
        </Shell>
      </Wrapper>
    );
    expect(screen.getByTestId("child")).toHaveTextContent("Content");
  });
});
