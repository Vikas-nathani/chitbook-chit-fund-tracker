import { createBrowserRouter, Navigate, Outlet, RouterProvider } from 'react-router-dom';
import { useAuth } from './auth';
import { Layout } from './components/Layout';
import { Login } from './pages/Login';
import { Signup } from './pages/Signup';
import { Dashboard } from './pages/Dashboard';
import { NewChit } from './pages/NewChit';
import { ChitGrid } from './pages/ChitGrid';
import { Insights } from './pages/Insights';

function RequireAuth() {
  const { session } = useAuth();
  return session ? <Outlet /> : <Navigate to="/login" replace />;
}

function GuestOnly() {
  const { session } = useAuth();
  return session ? <Navigate to="/" replace /> : <Outlet />;
}

// A data router is needed for useBlocker (unsaved-changes guard on the grid page)
const router = createBrowserRouter([
  {
    element: <GuestOnly />,
    children: [
      { path: '/login', element: <Login /> },
      { path: '/signup', element: <Signup /> },
    ],
  },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <Layout />,
        children: [
          { path: '/', element: <Dashboard /> },
          { path: '/new', element: <NewChit /> },
          { path: '/chits/:id', element: <ChitGrid /> },
          { path: '/insights', element: <Insights /> },
        ],
      },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
]);

export function App() {
  return <RouterProvider router={router} />;
}
