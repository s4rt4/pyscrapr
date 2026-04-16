import React from "react";
import { Button, Card, Code, Stack, Text, Title } from "@mantine/core";

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  State
> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <Card withBorder radius="lg" p="xl" m="md">
          <Stack align="center" gap="md">
            <Title order={3} c="red">Something went wrong</Title>
            <Text c="dimmed" ta="center" maw={500}>
              This page encountered an error. Other pages should still work.
            </Text>
            <Code block style={{ maxWidth: 600, overflow: "auto", fontSize: 11 }}>
              {this.state.error?.message || "Unknown error"}
            </Code>
            <Button
              variant="light"
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.reload();
              }}
            >
              Reload page
            </Button>
          </Stack>
        </Card>
      );
    }
    return this.props.children;
  }
}
