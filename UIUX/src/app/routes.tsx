import { createBrowserRouter } from "react-router";
import { Home } from "./pages/home";
import { Candidates } from "./pages/candidates";
import { Result } from "./pages/result";
import { History } from "./pages/history";
import { Dashboard } from "./pages/dashboard";
import { Root } from "./pages/root";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Root,
    children: [
      { index: true, Component: Home },
      { path: "candidates", Component: Candidates },
      { path: "result", Component: Result },
      { path: "history", Component: History },
      { path: "dashboard", Component: Dashboard },
    ],
  },
]);
