import { Navigate } from "react-router-dom";
import { useOrganizations, useProjects } from "../api/hooks";
import { EmptyState, ErrorState, Loading } from "../components/ui";

/** Sends the user to the first project of their first organization. */
export function HomeRedirect() {
  const orgs = useOrganizations();
  const org = orgs.data?.[0]?.slug;
  const projects = useProjects(org);

  if (orgs.error) return <ErrorState error={orgs.error} />;
  if (orgs.isLoading || (org && projects.isLoading)) return <Loading />;
  if (!org) return <EmptyState title="No organizations yet">Ask an owner to invite you.</EmptyState>;
  const project = projects.data?.[0]?.slug;
  if (!project) return <EmptyState title="No projects yet">Create one in the admin at /admin.</EmptyState>;
  return <Navigate to={`/${org}/${project}/issues`} replace />;
}
