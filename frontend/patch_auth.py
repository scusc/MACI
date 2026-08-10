import re

with open('src/app/core/auth.service.ts', 'r') as f:
    content = f.read()

get_token_old = """  getToken(): string | null {
    return localStorage.getItem('slice_token');
  }"""
get_token_new = """  getToken(): string | null {
    if (window.location.hostname === 'localhost') {
      return 'local-dummy-token';
    }
    return localStorage.getItem('slice_token');
  }"""
content = content.replace(get_token_old, get_token_new)

fetch_profile_old = """  fetchProfile(): Observable<User> {
    return this.http.get<User>(`${this.apiUrl}/me`).pipe("""
fetch_profile_new = """  fetchProfile(): Observable<User> {
    if (window.location.hostname === 'localhost') {
      const dummyUser: User = {
        id: 'local-test-id',
        email: 'testuser@example.com',
        first_name: 'Local',
        last_name: 'Dev',
        is_verified: true,
        kyc_status: 'verified',
        karma_score: 100
      };
      this.currentUser.set(dummyUser);
      return of(dummyUser);
    }
    return this.http.get<User>(`${this.apiUrl}/me`).pipe("""
content = content.replace(fetch_profile_old, fetch_profile_new)

with open('src/app/core/auth.service.ts', 'w') as f:
    f.write(content)

print("Patched auth.service.ts for local bypass")
