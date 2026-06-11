import { useNavigate } from "react-router-dom";

import { PageHeader } from "../components/PageHeader";
import { EmptyState } from "../components/ui/EmptyState";
import { Button } from "../components/ui/Button";

export function Forbidden() {
  const navigate = useNavigate();
  return (
    <>
      <PageHeader title="Access restricted" subtitle="This area requires an admin account." />
      <EmptyState
        title="You don't have access to this page."
        description="Your account role can't view this data. Contact an administrator if you believe this is a mistake."
        action={
          <Button variant="secondary" onClick={() => navigate("/")}>
            Back to dashboard
          </Button>
        }
      />
    </>
  );
}
