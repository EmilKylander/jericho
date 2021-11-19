FROM php:8.0-apache
WORKDIR /var/www/html

RUN echo "<Directory /var/www/html> " >> /etc/apache2/apache2.conf
RUN echo "Options Indexes FollowSymLinks" >> /etc/apache2/apache2.conf
RUN echo "AllowOverride All" >> /etc/apache2/apache2.conf
RUN echo "Require all granted" >> /etc/apache2/apache2.conf
RUN echo "</Directory>" >> /etc/apache2/apache2.conf

RUN a2enmod rewrite &&\
    service apache2 restart

COPY tests/assets/web-server .
EXPOSE 80