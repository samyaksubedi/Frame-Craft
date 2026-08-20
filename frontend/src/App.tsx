import { Navigate, Route, Routes, useParams } from "react-router-dom";
import { CreateStudio } from "./components/CreateStudio";
import { JobStudio } from "./components/JobStudio";

function JobRoute() {
  const { jobId } = useParams<{ jobId: string }>();
  return jobId ? <JobStudio jobId={jobId} /> : <Navigate to="/" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<CreateStudio />} />
      <Route path="/jobs/:jobId" element={<JobRoute />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
