package com.nival.chit.config;

import com.nival.chit.entity.User;
import com.nival.chit.enums.UserRoles;
import com.nival.chit.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * Bootstraps the platform admin account on startup.
 *
 * <p>Never deletes data. The admin is created only when no user with the configured
 * username exists, so restarts are safe. Credentials come from {@code app.admin.*}
 * (set through the {@code ADMIN_*} environment variables).</p>
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class DatabaseSeeder implements CommandLineRunner {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    @Value("${app.admin.username:}")
    private String adminUsername;

    @Value("${app.admin.password:}")
    private String adminPassword;

    @Value("${app.admin.name:Admin}")
    private String adminName;

    @Value("${app.admin.email:}")
    private String adminEmail;

    @Override
    @Transactional
    public void run(String... args) {
        if (adminUsername.isBlank() || adminPassword.isBlank()) {
            log.warn("app.admin.username/password not set. Skipping admin bootstrap.");
            return;
        }
        if (userRepository.findByUsername(adminUsername).isPresent()) {
            log.info("Admin user '{}' already exists. Skipping bootstrap.", adminUsername);
            return;
        }

        User admin = new User();
        admin.setName(adminName);
        admin.setUsername(adminUsername);
        admin.setEmail(adminEmail.isBlank() ? adminUsername + "@chitfund.local" : adminEmail);
        admin.setPassword(passwordEncoder.encode(adminPassword));
        admin.setRole(UserRoles.ADMIN);
        userRepository.save(admin);
        log.info("Admin user '{}' created.", adminUsername);
    }
}
