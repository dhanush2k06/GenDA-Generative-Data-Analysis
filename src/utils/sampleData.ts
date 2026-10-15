/**
 * High-quality synthetic CSV datasets for instant local exploration & verification.
 */

export function getSampleCsvFile(type: 'users' | 'messages' | 'synthetic'): File {
  if (type === 'users') {
    const content = `user_id,name,role,department,salary_usd,status,signup_date
u101,Sarah Connor,Lead Engineer,Engineering,145000,Active,2024-03-15
u102,John Doe,Data Scientist,Analytics,132000,Active,2024-04-01
u103,Alice Johnson,Product Manager,Product,128000,Active,2024-05-12
u104,Bob Williams,Security Architect,Engineering,155000,Active,2024-06-20
u105,Clara Oswald,Frontend Developer,Engineering,115000,Inactive,2024-07-08
u106,David Miller,Growth Analyst,Analytics,98000,Active,2024-08-14
u107,Elena Rostova,UX Designer,Product,110000,Active,2024-09-01
u108,Frank Castle,DevOps Specialist,Engineering,138000,Active,2024-09-18
u109,Grace Hopper,Chief Scientist,Analytics,190000,Active,2024-10-05
u110,Henry Ford,Operations Lead,Operations,105000,Active,2024-11-20`;
    return new File([content], 'users_workforce.csv', { type: 'text/csv' });
  }

  if (type === 'messages') {
    const content = `message_id,category,priority,read_count,response_time_ms,is_urgent,date
m101,Transaction,High,342,120,True,2025-01-10
m102,Newsletter,Low,12,850,False,2025-01-11
m103,Security Alert,Critical,985,45,True,2025-01-15
m104,Transaction,High,410,110,True,2025-01-18
m105,Support,Medium,88,320,False,2025-01-22
m106,Newsletter,Low,15,920,False,2025-02-02
m107,Security Alert,Critical,1120,38,True,2025-02-05
m108,Support,Medium,95,290,False,2025-02-12
m109,Transaction,High,520,105,True,2025-02-20
m110,Support,Medium,102,310,False,2025-02-25`;
    return new File([content], 'messages_telemetry.csv', { type: 'text/csv' });
  }

  // Known-answer benchmark dataset
  const content = `category,amount,date
A,10,2025-01-01
A,20,2025-01-05
A,30,2025-01-10
B,40,2025-02-01
B,,2025-02-15`;
  return new File([content], 'benchmark_synthetic.csv', { type: 'text/csv' });
}
