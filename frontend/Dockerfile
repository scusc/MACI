# Serve the Angular application with Nginx Alpine
FROM nginx:alpine

# Copy prebuilt dist output directly to nginx html directory
COPY dist/frontend/browser /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
