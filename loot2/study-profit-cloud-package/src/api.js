export const getProjects = () => fetch('/api/projects').then((response) => response.json())
