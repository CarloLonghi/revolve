/*
 * Copyright (C) 2015-2021 Vrije Universiteit Amsterdam
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * Author: Matteo De Carlo
 * Date: May 28, 2021
 *
 */
#ifndef REVOLVE_ADDRESS_H
#define REVOLVE_ADDRESS_H

#include <string>
#include <vector>
#include <netdb.h>

namespace revolve::utils {

class Address {
public:
    enum IPVersion { IPv4, IPv6, EITHER };

private:
    std::string _hostname;
    IPVersion _ip_version;
    addrinfo *_addrinfo = nullptr;

public:
    explicit Address(std::string hostname, IPVersion ipVersion = EITHER);

    ~Address();

    [[nodiscard]] std::vector<const sockaddr*> get_ips() const;
    [[nodiscard]] std::vector<std::string> get_ips_str() const;
};


}

#endif //REVOLVE_ADDRESS_H