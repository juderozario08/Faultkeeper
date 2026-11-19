import styled from "@emotion/styled";
import { NavLink, Outlet, useNavigate, useParams } from "react-router-dom";
import { useLogout, useMe, useProjects } from "../api/hooks";
import { color } from "../theme/tokens";
import { ThemeToggle } from "./ThemeToggle";
import { Button, Select } from "./ui";

const Shell = styled.div`
  min-height: 100%;
  display: flex;
  flex-direction: column;
`;

const Header = styled.header`
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 20px;
  background: ${color.bgElevated};
  border-bottom: 1px solid ${color.border};
  position: sticky;
  top: 0;
  z-index: 10;
  flex-wrap: wrap;
`;

const Brand = styled(NavLink)`
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  font-size: 15px;
  color: ${color.text};
  &:hover {
    text-decoration: none;
  }
`;

const Logo = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden>
    <path d="M12 2 3 6v6c0 5 3.8 9.3 9 10 5.2-.7 9-5 9-10V6l-9-4Z" style={{ fill: color.accentAlt }} />
    <path d="M12 7v6m0 3.2v.3" style={{ stroke: color.bgElevated }} strokeWidth="2.2" strokeLinecap="round" fill="none" />
  </svg>
);

const Nav = styled.nav`
  display: flex;
  gap: 4px;
  a {
    color: ${color.textMuted};
    padding: 5px 10px;
    border-radius: 6px;
    font-weight: 500;
  }
  a:hover {
    color: ${color.text};
    background: ${color.surfaceHover};
    text-decoration: none;
  }
  a.active {
    color: ${color.text};
    background: ${color.surface};
  }
`;

const Spacer = styled.div`
  flex: 1;
`;

const Main = styled.main`
  flex: 1;
  width: 100%;
  max-width: 1280px;
  margin: 0 auto;
  padding: 20px;
`;

export function Layout() {
  const { org = "", project = "" } = useParams();
  const navigate = useNavigate();
  const projects = useProjects(org);
  const me = useMe();
  const logout = useLogout();

  return (
    <Shell>
      <Header>
        <Brand to="/">
          <Logo />
          Faultkeeper
        </Brand>
        {projects.data && (
          <Select
            aria-label="Project"
            value={project}
            onChange={(e) => navigate(`/${org}/${e.target.value}/issues`)}
          >
            {projects.data.map((p) => (
              <option key={p.id} value={p.slug}>
                {p.name}
              </option>
            ))}
          </Select>
        )}
        <Nav>
          <NavLink to={`/${org}/${project}/issues`}>Issues</NavLink>
          <NavLink to={`/${org}/${project}/settings`}>Settings</NavLink>
        </Nav>
        <Spacer />
        <ThemeToggle />
        {me.data && (
          <Button variant="ghost" size="sm" onClick={() => logout.mutate(undefined, { onSuccess: () => navigate("/login") })}>
            Sign out {me.data.email}
          </Button>
        )}
      </Header>
      <Main>
        <Outlet />
      </Main>
    </Shell>
  );
}
