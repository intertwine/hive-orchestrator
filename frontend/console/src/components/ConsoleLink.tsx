import {
  Link,
  type LinkProps,
  NavLink,
  type NavLinkProps,
  type To,
  useLocation,
} from "react-router-dom";

export function preserveConsoleSearch(to: To, search: string): To {
  if (!search) {
    return to;
  }

  if (typeof to === "string") {
    const hashIndex = to.indexOf("#");
    const hash = hashIndex >= 0 ? to.slice(hashIndex) : "";
    const base = hashIndex >= 0 ? to.slice(0, hashIndex) : to;
    if (base.includes("?")) {
      return to;
    }
    return `${base}${search}${hash}`;
  }

  if (to.search !== undefined) {
    return to;
  }

  return { ...to, search };
}

export function ConsoleLink(props: LinkProps) {
  const location = useLocation();
  return <Link {...props} to={preserveConsoleSearch(props.to, location.search)} />;
}

export function ConsoleNavLink(props: NavLinkProps) {
  const location = useLocation();
  return <NavLink {...props} to={preserveConsoleSearch(props.to, location.search)} />;
}
