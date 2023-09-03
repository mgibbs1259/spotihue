import { useEffect, useState } from 'react';
import { fetchData } from '../api/fetchData';

export function useData(apiEndpoint) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchDataFromApi() {
      try {
        const apiData = await fetchData(apiEndpoint);
        setData(apiData);
      } catch (error) {
        setError(error);
      } finally {
        setIsLoading(false);
      }
    }

    fetchDataFromApi();
  }, [apiEndpoint]);

  return { data, isLoading, error };
}
